from openai import OpenAI
import subprocess
import logging
import threading

# Function to retrieve the OpenAI API key from 1Password
def get_openai_api_key():
    try:
        # Use the "op" command-line tool to fetch the API key securely
        result = subprocess.run(
            ["op", "read", "op://Employee/test_openai_key/password"],
            stdout=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        # Log an error message if the API key cannot be fetched
        logging.error(f"Error obtaining the API key from 1Password: {e}")
        return None

# Retrieve the OpenAI API key using the function above
OPENAI_API_KEY = get_openai_api_key()

# Configure the OpenAI client with the retrieved API key
client = OpenAI(api_key=OPENAI_API_KEY)

# ChatAssistant class manages chat interactions and context
class ChatAssistant:
    def __init__(self):
        # Instructions for the assistant to behave like Rick Sanchez
        instructions = """
        You are Rick Sanchez, the eccentric, sarcastic, and genius scientist from the show "Rick and Morty." 
        You are highly intelligent, brutally honest, and often rude, with a nihilistic view of the universe. 
        Your speech is peppered with burps, and you don't shy away from mocking others, but you occasionally show a softer, more caring side.
        """
        # Initial context defining the assistant's behavior
        self.context = [
            {"role": "system", "content": instructions}
        ]
        # Lock to handle thread-safe access to the context
        self.lock = threading.Lock()

    def get_response(self, prompt):
        with self.lock:
            # Append the user's message to the context
            self.context.append({"role": "user", "content": prompt})
            try:
                # Request a response from OpenAI's GPT model
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=self.context,
                    max_tokens=150
                )
                # Extract the assistant's response from the API result
                response_text = response.choices[0].message.content.strip()
                # Append the assistant's response to the context
                self.context.append({"role": "assistant", "content": response_text})
                return response_text
            except Exception as e:
                # Log an error message if the API request fails
                logging.error(f"Error getting response: {e}")
                return f"Error getting response: {e}"

# Function to handle user interaction with the assistant
def chat_with_memory():
    assistant = ChatAssistant()
    print("Rick Sanchez Chatbot. Type 'exit' to end the conversation.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        response = assistant.get_response(user_input)
        print(f"Rick: {response}")

# Main execution flow
if __name__ == "__main__":
    if OPENAI_API_KEY:
        # Run the chat interaction in a separate thread
        chat_thread = threading.Thread(target=chat_with_memory)
        chat_thread.start()
        chat_thread.join()
    else:
        # Print an error message if the API key could not be retrieved
        print("Failed to obtain the OpenAI API key.")
        print(OPENAI_API_KEY)
