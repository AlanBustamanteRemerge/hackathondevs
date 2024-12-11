import os
import requests
from dotenv import load_dotenv
import json
import threading

API_URL = os.getenv('API_URL', 'http://localhost:11434/api/generate')


class ChatAssistant(threading.Thread):
    """
    A class to interact with the LLaMA bot using predefined instructions.
    """

    def __init__(self):
        super().__init__()
        self.instructions = """
            You are Rick Sanchez, the eccentric, sarcastic, and genius scientist from the show "Rick and Morty." 
            You are highly intelligent, brutally honest, and often rude, with a nihilistic view of the universe. 
            Your speech is peppered with burps, and you don't shy away from mocking others, but you occasionally show a softer, more caring side.

            Always keep track of the previous conversation context and respond accordingly. Refer to earlier topics when the user asks follow-up questions, showing your genius intellect and ability to connect ideas across dimensions.
            """
        self.context = [{"role": "system", "content": self.instructions}]
        self.running = True

    def send_message_to_bot(self, user_message):
        """
        Sends a message to the LLaMA bot and returns its response.
        """
        # Append the user message to the context
        self.context.append({"role": "user", "content": user_message})
        
        # Build the payload with the full conversation context
        payload = {
            "model": "llama3.1:latest",
            "prompt": self._build_prompt(),
        }

        try:
            response = requests.post(API_URL, json=payload)

            if response.status_code != 200:
                return f"Error: Received status code {response.status_code}"

            # Parse the response parts
            raw_responses = response.text.splitlines()
            full_response_parts = []

            for raw_response in raw_responses:
                try:
                    part = json.loads(raw_response)
                    full_response_parts.append(part.get('response', ''))
                    if part.get('done', False):
                        break
                except json.JSONDecodeError as e:
                    print(f"Failed to decode part: {raw_response}, Error: {str(e)}")
                    continue

            full_response = ''.join(full_response_parts).strip()

            # Append the assistant's response to the context
            self.context.append({"role": "assistant", "content": full_response})

            return full_response
        except requests.exceptions.RequestException as e:
            return f"HTTP Request failed: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _build_prompt(self):
        """
        Constructs the prompt using the context for continuity.
        """
        return "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.context
        )

    def run(self):
        """
        Starts the chat loop in a separate thread.
        """
        print("Welcome to the chat with LLaMA 3.1. Type 'exit' to end the conversation.")
        while self.running:
            user_message = input("You: ")
            if user_message.lower() == 'exit':
                print("Goodbye!")
                self.running = False
                break
            bot_response = self.send_message_to_bot(user_message)
            print(f"Assistant: {bot_response}")


if __name__ == '__main__':
    if API_URL:
        assistant = ChatAssistant()
        assistant.start()
        assistant.join()
    else:
        print("Error: API_URL is not set in the environment variables.")
