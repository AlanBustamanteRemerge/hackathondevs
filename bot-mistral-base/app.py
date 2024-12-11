import os
import requests
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Get the API URL from the environment variables
API_URL = os.getenv('API_URL', 'http://localhost:11434/api/generate')

def send_message_to_bot(message):
    payload = {
        "model": "mistral:latest",
        "prompt": message
    }

    try:
        response = requests.post(API_URL, json=payload)
        
        # Check if the response status code is not 200 (OK)
        if response.status_code != 200:
            return f"Error: Received status code {response.status_code}"

        # Aggregate the response parts
        raw_responses = response.text.splitlines()
        full_response_parts = []

        for raw_response in raw_responses:
            try:
                part = json.loads(raw_response)
                full_response_parts.append(part.get('response', ''))
                # Check if this is the final part of the response
                if part.get('done', False):
                    break
            except json.JSONDecodeError as e:
                print(f"Failed to decode part: {raw_response}, Error: {str(e)}")
                continue

        full_response = ''.join(full_response_parts).strip()
        return full_response
    except requests.exceptions.RequestException as e:
        return f"HTTP Request failed: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    print("Welcome to the chat with Mistral Type 'exit' to end the conversation.")
    
    while True:
        user_message = input("You: ")
        if user_message.lower() == 'exit':
            break
        bot_response = send_message_to_bot(user_message)
        print(f"Mistral: {bot_response}")
