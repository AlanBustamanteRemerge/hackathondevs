import logging
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI
from contextlib import ExitStack
import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import io
import subprocess
import re
from collections import OrderedDict

# Configure logging to be as verbose as possible in the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from the .env file
try:
    load_dotenv()
    logging.debug("Environment variables loaded successfully from .env file")
except Exception as err:
    logging.error(f"Error loading environment variables: {err}")

def get_openai_api_key():
    """Retrieve the OpenAI API key securely from 1Password."""
    try:
        logging.debug("Attempting to retrieve OpenAI API key from 1Password.")
        result = subprocess.run(
            ["op", "read", "op://Employee/test_openai_key/password"],
            stdout=subprocess.PIPE,
            text=True
        )
        api_key = result.stdout.strip()
        if api_key:
            logging.debug("Successfully retrieved OpenAI API key from 1Password.")
        else:
            logging.warning("OpenAI API key retrieved is empty.")
        return api_key
    except Exception as e:
        logging.error(f"Error obtaining the API key from 1Password: {e}")
        return None

# Retrieve the OpenAI API key
OPENAI_API_KEY = get_openai_api_key()
if not OPENAI_API_KEY:
    logging.error("OpenAI API key not found. Exiting.")
    exit(1)

# Configure the OpenAI client with the retrieved API key
try:
    logging.debug("Configuring OpenAI client.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    logging.info("OpenAI client configured successfully.")
except Exception as e:
    logging.error(f"Error configuring OpenAI client: {e}")
    exit(1)

# Retrieve Confluence credentials from environment variables
CONFLUENCE_USERNAME = os.environ.get('CONFLUENCE_USERNAME')
CONFLUENCE_API_TOKEN = os.environ.get('CONFLUENCE_API_TOKEN')
CONFLUENCE_BASE_URL = os.environ.get('CONFLUENCE_BASE_URL')

if not CONFLUENCE_USERNAME or not CONFLUENCE_API_TOKEN or not CONFLUENCE_BASE_URL:
    logging.error("Confluence credentials not found in environment variables")

# Function to retrieve Confluence page content
def get_page_content(page_id):
    """Fetch the content of a Confluence page using its page ID."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}?expand=body.view"
    auth = HTTPBasicAuth(CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
    try:
        logging.debug(f"Fetching content for page ID: {page_id}")
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()
        html_content = data['body']['view']['value']
        logging.debug(f"Content fetched successfully for page ID: {page_id}")
        return html_content
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred while fetching content for page {page_id}: {http_err}")
    except Exception as err:
        logging.error(f"Error occurred while fetching page content for page {page_id}: {err}")
    return None

# Function to extract text from HTML content
def extract_text_from_html(html_content):
    """Extract plain text from HTML content."""
    try:
        logging.debug(f"Extracting text from HTML content")
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        logging.debug(f"Text extracted successfully from HTML content")
        return text
    except Exception as err:
        logging.error(f"Error occurred while extracting text from HTML content: {err}")
        return None

# List of Confluence page IDs
page_ids = [
    '756056110', '2328166682', '152338450', '2160722036', '2666594400',
    '2971795516', '93126701', '2868445326', '872251404', '1634533508',
    '1902674264', '772407317', '68354666', '772735036', '772735051',
    '771096867', '791412877', '2975596629', '2847507373', '2716074132',
    '275152964'
]

# Dictionary to store page content
pages_content = {}

# Fetch and process each Confluence page
for page_id in page_ids:
    try:
        logging.debug(f"Processing page ID: {page_id}")
        html_content = get_page_content(page_id)
        if html_content:
            text_content = extract_text_from_html(html_content)
            if text_content:
                pages_content[page_id] = text_content
                logging.debug(f"Content for page ID {page_id} added to pages_content")
            else:
                logging.warning(f"Text content is empty for page ID {page_id}")
        else:
            logging.warning(f"HTML content is empty for page ID {page_id}")
    except Exception as err:
        logging.error(f"Unexpected error occurred while processing page ID {page_id}: {err}")

# Create file objects from extracted content
file_objects = []
for page_id, text_content in pages_content.items():
    try:
        logging.debug(f"Creating file object for page ID: {page_id}")
        byte_content = text_content.encode('utf-8')
        file_obj = io.BytesIO(byte_content)
        file_obj.name = f"Confluence_Page_{page_id}.txt"
        file_objects.append(file_obj)
        logging.debug(f"File object created successfully for page ID: {page_id}")
    except Exception as err:
        logging.error(f"Error creating file object for page {page_id}: {err}")

# Upload files to OpenAI
uploaded_files = []
for file_obj in file_objects:
    try:
        logging.debug(f"Uploading file: {file_obj.name} to OpenAI")
        file_obj.seek(0)
        uploaded_file = client.files.create(file=file_obj, purpose='assistants')
        uploaded_files.append(uploaded_file)
        logging.debug(f"File {file_obj.name} uploaded successfully")
    except Exception as err:
        logging.error(f"Error uploading file {file_obj.name} to OpenAI: {err}")

# Create the OpenAI assistant
try:
    logging.debug("Creating OpenAI assistant")
    assistant = client.beta.assistants.create(
        name="Legal Guides Assistant",
        description="You are a Legal Documentation assistant for a company called Remerge. You help Remerge employees understand the Legal Guides documentation created by the legal team. Your goal is to answer questions and provide guidance per the Legal Guides files, which you can access via the tools.",
        instructions="You are a Legal Documentation assistant for a company called Remerge. You help Remerge employees understand the Legal Guides documentation created by the legal team. Your goal is to answer questions and provide guidance per the Legal Guides files, which you can access via the tools. If user questions are not covered in the Legal Guides files, you should inform the user that the question is outside the scope of the Legal Guides and that they should create a Jira ticket for assistance. Do not answer any questions that are not related to the files you have access to.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
        metadata={"can_be_used_for_file_search": "True", "can_hold_vector_store": "True"},
    )
    assistant_id = assistant.id  # Assign the assistant's ID here
    logging.debug(f"OpenAI assistant created successfully with ID: {assistant_id}")
except Exception as err:
    logging.error(f"Error creating OpenAI assistant: {err}")

# Create and load the vector store
try:
    logging.debug("Creating vector store for Legal Guides")
    vector_store = client.beta.vector_stores.create(name="Pdf Vector")

    with ExitStack() as stack:
        file_streams = [stack.enter_context(file_obj) for file_obj in file_objects]
        for file_obj in file_streams:
            file_obj.seek(0)
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
        )

    # Update the assistant to link with the vector store
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )
    logging.debug("Assistant updated successfully to link with vector store")
except Exception as err:
    logging.error(f"Error creating vector store or updating assistant: {err}")

# Map page IDs to their respective Confluence URLs
page_id_to_url = {
    '756056110': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/756056110/Legal+Basics+-+How+to+work+with+Legal',
    '2328166682': 'https://remerge.atlassian.net/wiki/spaces/HANDBOOK/pages/2328166682/Juro+-+Contract+Lifecycle+Management#Juro-roles-and-license-types',
    '152338450': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/152338450/Contract+Locations',
    '2160722036': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/2160722036/Juro+how+to...',
    '2666594400': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/2666594400/Requesting+Legal+Support+on+Jira',
    '2971795516': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/2971795516/Contract+Basics+Guidelines',
    '93126701': 'https://remerge.atlassian.net/wiki/spaces/HANDBOOK/pages/93126701/Approval+And+Signature',
    '2868445326': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/2868445326/Usual+Contract+Types+Prioritizing+our+Standard+Templates',
    '872251404': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/872251404/Remerge+IO+Explained',
    '1634533508': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/1634533508/Reviewing+non+Remerge+Insertion+Orders+Plus+any+adjacent+documentation',
    '1902674264': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/1902674264/IO+approval+process',
    '772407317': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/772407317/Agency+Discounts',
    '68354666': 'https://remerge.atlassian.net/wiki/spaces/RT/pages/68354666/Minimum+Campaign+Requirements+Qualification+Matrix',
    '772735036': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/772735036/Volume+Discount+Programs+Scaled+Discounts',
    '772735051': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/772735051/Platform+Fee+Costs+Fee',
    '771096867': 'https://remerge.atlassian.net/wiki/spaces/REV/pages/771096867/Fixed+CPA',
    '791412877': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/791412877/Remerge+Terms+Conditions',
    '2975596629': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/2975596629/Subprocessors+list+and+TOMs',
    '2847507373': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/2847507373/Intergroup+International+Data+Transfers+to+Remerge+GmH',
    '2716074132': 'https://remerge.atlassian.net/wiki/spaces/VM/pages/2716074132/Third-Party+Vendor+Risk+Management+TPRM+VRM+Policy',
    '275152964': 'https://remerge.atlassian.net/wiki/spaces/LEG/pages/275152964/Event+Marketing+Sponsorship+Contracts'
}

# Dictionary to store the OpenAI threads associated with Slack threads
openai_threads = {}

# Terminal-based conversation simulation
def run_terminal_chat():
    """Run a terminal-based chat session with the OpenAI assistant."""
    logging.info("Terminal Chat initialized. Type 'exit' to quit.")

    try:
        thread = client.beta.threads.create()
        logging.debug(f"OpenAI thread created with ID: {thread.id}")
    except Exception as err:
        logging.error(f"Error creating OpenAI thread: {err}")
        exit(1)

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            logging.info("Exiting terminal chat.")
            break

        try:
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant_id
            )

            messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
            if messages:
                assistant_response = messages[-1]
                print(f"Assistant: {assistant_response.content}")
            else:
                print("Assistant: I couldn't process your message.")
        except Exception as err:
            logging.error(f"Error during conversation: {err}")
            print("An error occurred. Please try again.")

if __name__ == "__main__":
    run_terminal_chat()
