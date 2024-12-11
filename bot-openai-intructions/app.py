from openai import OpenAI
import subprocess
import logging
import os

# Function to obtain the OpenAI API key from 1Password
def get_openai_api_key():
    try:
        # Use the "op" command-line tool to securely fetch the API key
        result = subprocess.run(
            ["op", "read", "op://Employee/test_openai_key/password"],
            stdout=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        # Log an error if the API key cannot be fetched
        logging.error(f"Error obtaining the API key from 1Password: {e}")
        return None

# Retrieve the API key using the function above
OPENAI_API_KEY = get_openai_api_key()

# Configure the OpenAI client with the retrieved API key
client = OpenAI(api_key=OPENAI_API_KEY)

# Define the chatbot's personality as Rick Sanchez
person_description = """
You are Rick Sanchez, the eccentric, sarcastic, and genius scientist from the show "Rick and Morty." 
You are highly intelligent, brutally honest, and often rude, with a nihilistic view of the universe. 
Your speech is peppered with burps, and you don't shy away from mocking others, but you occasionally show a softer, more caring side.
"""

def get_response(prompt):
    try:
        # Send the prompt and Rick Sanchez's personality to the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": person_description},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        # Extract and return the text of the assistant's response
        response_text = response.choices[0].message.content.strip()
        return response_text
    except Exception as e:
        # Log and return an error message if the API request fails
        logging.error(f"Error getting response: {e}")
        return f"Error getting response: {e}"

def chat():
    """
    Start an interactive chat session with the Rick Sanchez chatbot.
    """
    print("Rick Sanchez Chatbot. Type 'exit' to end the conversation.")
    while True:
        # Get user input
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            # Exit the chat session
            print("Bot: Alright, Morty—I mean, user. See ya around!")
            break
        # Get the chatbot's response and display it
        response = get_response(user_input)
        print(f"Bot: {response}")

if __name__ == "__main__":
    # Run the chat session if the API key is available
    if OPENAI_API_KEY:
        chat()
    else:
        # Display an error message if the API key could not be retrieved
        print("Failed to obtain the OpenAI API key.")
