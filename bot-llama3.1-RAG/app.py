import os
import requests
from dotenv import load_dotenv
import json
import threading
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import logging
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm
from typing import List

# Load environment variables from a .env file
load_dotenv()
API_URL = os.getenv('API_URL', 'http://localhost:11434/api/generate')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME')
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_API_TOKEN')
CONFLUENCE_BASE_URL = os.getenv('CONFLUENCE_BASE_URL')
VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './vector_db')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'confluence_pages')

# Configure logging to display relevant information
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatAssistant(threading.Thread):
    def __init__(self):
        super().__init__()
        self.instructions = """
            You are an intelligent, polite, and helpful assistant. Your goal is to provide clear, concise, and accurate information 
            to the user. Always maintain a professional tone and ensure that your responses are relevant to the user's questions.
            If the user asks follow-up questions, connect them to the context of the previous conversation to ensure continuity.
        """
        # Context to maintain the flow of conversation
        self.context = [{"role": "system", "content": self.instructions}]
        self.running = True
        self.confluence_pages = {}

        # Initialize ChromaDB client with a persistent storage path
        self.vs_client = chromadb.PersistentClient(
            path=VECTOR_DB_PATH, settings=chromadb.Settings(allow_reset=True)
        )
        # Define the embedding function for creating vector representations
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL, trust_remote_code=True
        )
        self.collection = None

    # Set or create a vector collection
    def set_collection(self, collection_name: str, embedding_model: str = None) -> None:
        if embedding_model:
            self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model, trust_remote_code=True
            )
        self.collection = self.vs_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_func,
            metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL},
        )
        logging.info(f"Set Collection: {collection_name}. Embedding Model: {EMBEDDING_MODEL}")

    # Create a collection by embedding Confluence page content
    def make_collection(self, confluence_data: dict, collection_name: str) -> None:
        if not confluence_data:
            logging.error("No data provided to create the collection.")
            return

        self.set_collection(collection_name)

        for page_id, content in confluence_data.items():
            chunks = content.split("\n")
            logging.info(f"Embedding and storing content for page ID: {page_id}...")

            for i, chunk in tqdm(enumerate(chunks, 1), total=len(chunks)):
                if not chunk.strip():  # Skip empty lines
                    continue

                metadata = {"source": page_id, "part": i}
                try:
                    self.collection.add(
                        documents=[chunk],  # Must be a list
                        ids=[f"id_{page_id}_{i}"],  # Must be a list
                        metadatas=[metadata],  # Must be a list
                    )
                    logging.info(f"Stored vector for page ID: {page_id}, part: {i}.")
                except Exception as e:
                    logging.error(f"Failed to store vector for page ID: {page_id}, part: {i}. Error: {e}")

        logging.info(f"Collection '{collection_name}' created with embedded data.")

    # Prepare the vector database for searching
    def setup_vec_store(self, collection_name: str = COLLECTION_NAME) -> None:
        if not os.path.exists(VECTOR_DB_PATH):
            try:
                os.makedirs(VECTOR_DB_PATH)
                logging.info(f"Created vector database directory at {VECTOR_DB_PATH}.")
            except Exception as e:
                logging.error(f"Failed to create vector database directory at {VECTOR_DB_PATH}: {e}")
                raise
        
        if not self.confluence_pages:
            logging.error("No data found in 'self.confluence_pages'. Cannot create vector store.")
            return
        
        logging.info("Initializing vector database...")
        self.make_collection(self.confluence_pages, collection_name)

    # Search the vector store for a query
    def search_vector_store(self, query: str):
        logging.info(f"Searching vector store for query: {query}")
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=5
            )
            return results.get("documents", [])
        except Exception as e:
            logging.error(f"Failed to search vector store. Error: {e}")
            return []

    # Fetch Confluence pages by ID and store their content
    def fetch_confluence_pages(self, page_ids):
        if not page_ids:
            logging.error("No page IDs provided for fetching.")
            return

        for page_id in page_ids:
            url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}?expand=body.view"
            auth = HTTPBasicAuth(CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
            try:
                response = requests.get(url, auth=auth)
                response.raise_for_status()
                data = response.json()
                html_content = data.get('body', {}).get('view', {}).get('value', '')
                if not html_content:
                    logging.warning(f"No content found for page ID: {page_id}. Skipping.")
                    continue

                text_content = self.extract_text_from_html(html_content)
                self.confluence_pages[page_id] = text_content
                logging.info(f"Fetched and stored content for page ID: {page_id}")
            except Exception as e:
                logging.error(f"Error fetching page {page_id}: {e}")

    # Extract plain text from HTML content
    @staticmethod
    def extract_text_from_html(html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        except Exception as e:
            logging.error(f"Error extracting text: {e}")
            return None

    # Run the chat assistant to interact with the user
    def run(self):
        print("Welcome to the chat with LLaMA 3.1. Type 'exit' to end the conversation.")
        while self.running:
            user_message = input("You: ")
            if user_message.lower() == 'exit':
                print("Goodbye!")
                self.running = False
                break
            
            # Search the vector store for relevant information
            results = self.search_vector_store(user_message)
            if results:
                response = "\n\n\n".join([f"Result: {doc}" for doc in results])
            else:
                response = "Sorry, I couldn't find relevant information."

            print(f"Assistant: {response}")

# Entry point to initialize and run the assistant
if __name__ == '__main__':
    if API_URL and CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN and CONFLUENCE_BASE_URL:
        assistant = ChatAssistant()

        # Fetch Confluence pages and set up vector store
        page_ids = [
            '756056110', '2328166682', '152338450', '2160722036', '2666594400',
            '2971795516', '93126701', '2868445326', '872251404', '1634533508',
            '1902674264', '772407317', '68354666', '772735036', '772735051',
            '771096867', '791412877', '2975596629', '2847507373', '2716074132',
            '275152964'
        ]
        assistant.fetch_confluence_pages(page_ids)
        assistant.setup_vec_store(COLLECTION_NAME)

        assistant.start()
        assistant.join()
    else:
        print("Error: Missing required environment variables.")
