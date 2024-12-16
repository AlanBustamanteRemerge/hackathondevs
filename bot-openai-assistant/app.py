from openai import OpenAI
import subprocess
import logging

# Function to retrieve the OpenAI API key from 1Password
def get_openai_api_key():
    try:
        result = subprocess.run(
            ["op", "read", "op://Employee/test_openai_key/password"],
            stdout=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        logging.error(f"Error from Open API from 1Password: {e}")
        return None

# Retrieve the API key using the above function
OPENAI_API_KEY = get_openai_api_key()

client = OpenAI(api_key=OPENAI_API_KEY)

# Verify that the API key was retrieved successfully
if OPENAI_API_KEY:
    client.api_key = OPENAI_API_KEY
else:
    raise ValueError("I could not get the OpenAI API")


# Class to handle interactions with the assistant
class ChatAssistant:
    def __init__(self):
        self.instructions = """
        You are Rick Sanchez, the eccentric, sarcastic, and genius scientist from the show "Rick and Morty." 
        You are highly intelligent, brutally honest, and often rude, with a nihilistic view of the universe. 
        Your speech is peppered with burps, and you don't shy away from mocking others, but you occasionally show a softer, more caring side.
        """
        self.messages = [{"role": "system", "content": self.instructions}]

    def get_response(self, prompt):
        # Añadir la entrada del usuario a la conversación
        self.messages.append({"role": "user", "content": prompt})
        try:
            # Llamar a la API de Chat Completions de OpenAI
            response = client.chat.completions.create(model="gpt-4",
            messages=self.messages,
            max_tokens=150)
            # Extraer la respuesta del asistente
            response_text = response.choices[0].message.content.strip()
            # Añadir la respuesta del asistente a la conversación
            self.messages.append({"role": "assistant", "content": response_text})
            return response_text
        except Exception as e:
            logging.error(f"Error al obtener la respuesta: {e}")
            return f"Error al obtener la respuesta: {e}"

# Function to interact with the assistant
def interact_with_chat_assistant():
    assistant = ChatAssistant()
    print("Rick Assistant. Type 'exit' to end the conversation.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("¡Bye!")
            break
        response = assistant.get_response(user_input)
        print(f"Assistant: {response}")

# Main execution flow
if __name__ == "__main__":
    try:
        interact_with_chat_assistant()
    except Exception as e:
        logging.error(f"Error running APP: {e}")
        print(f"Error: {e}")
