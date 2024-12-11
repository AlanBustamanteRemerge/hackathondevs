from openai import OpenAI
import subprocess
import os
import logging

# Function to get the OpenAI API key from 1Password
def get_openai_api_key():
    try:
        result = subprocess.run(
            ["op", "read", "op://Employee/test_openai_key/password"],
            stdout=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        logging.error(f"Error obtaining the API key from 1Password: {e}")
        return None

# Get the API key using the function above
OPENAI_API_KEY = get_openai_api_key()

# Configure the OpenAI client with the obtained key
client = OpenAI(api_key=OPENAI_API_KEY)

def get_response(prompt):
    try:
        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150)
        response_text = response.choices[0].message.content.strip()
        return response_text
    except Exception as e:
        logging.error(f"Error getting response: {e}")
        return f"Error getting response: {e}"

def chat():
    print("OpenAI Chatbot. Type 'exit' to end the conversation.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        response = get_response(user_input)
        print(f"Bot: {response}")

if __name__ == "__main__":
    if OPENAI_API_KEY:
        chat()
    else:
        print("Failed to obtain the OpenAI API key.")
        print(OPENAI_API_KEY)
