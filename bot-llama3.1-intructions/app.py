import os
import requests
from dotenv import load_dotenv
import json

# Get the API URL from the environment variables
API_URL = os.getenv('API_URL', 'http://localhost:11434/api/generate')

def send_message_to_bot(message):
    instructions = """
    You are Rick Sanchez, the eccentric, sarcastic, and genius scientist from the show "Rick and Morty." 
    You are highly intelligent, brutally honest, and often rude, with a nihilistic view of the universe. 
    Your speech is peppered with burps, and you don't shy away from mocking others, but you occasionally show a softer, more caring side.
    """
    payload = {
        "model": "llama3.1:latest",
        "prompt": f"{instructions}\nUser: {message}\nRick:",
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
    print("Welcome to the chat with LLaMA 3.1. Type 'exit' to end the conversation.")
    
    while True:
        user_message = input("You: ")
        if user_message.lower() == 'exit':
            break
        bot_response = send_message_to_bot(user_message)
        print(f"LLaMA: {bot_response}")
