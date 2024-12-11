import base64
import requests
import os
import json
from flask import Flask, request, jsonify

# Configure the base URL for the Llama 3.2 Vision model
MODEL_URL = "http://localhost:11434/api/chat"

app = Flask(__name__)

def encode_image_to_base64(image_path):
    """Converts an image to base64."""
    try:
        print(f"Attempting to access file at: {image_path}")  # Debugging line
        # Check if the file exists before trying to open it
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File does not exist: {image_path}")
        
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Image file not found at: {image_path}")
    except Exception as e:
        raise RuntimeError(f"Error encoding image: {str(e)}")

def query_llama_vision(prompt, image_path=None):
    """Queries the Llama 3.2 Vision model."""
    messages = [{"role": "user", "content": prompt}]
    
    if image_path:
        try:
            encoded_image = encode_image_to_base64(image_path)
            messages[0]["images"] = [encoded_image]
        except Exception as e:
            return {"error": str(e)}

    payload = {
        "model": "llama3.2-vision",
        "messages": messages
    }

    print(f"Payload: {payload}")  # Debugging line

    try:
        # Send the request to the model with streaming support
        response = requests.post(MODEL_URL, json=payload, stream=True)

        # Check the response status code
        if response.status_code != 200:
            return {"error": f"Error {response.status_code}: {response.text}"}

        # Process the streaming response
        result = []
        for line in response.iter_lines():
            if line:  # Ignor empty lines
                try:
                    part = json.loads(line)
                    content = part.get("message", {}).get("content", "")
                    result.append(content)
                except json.JSONDecodeError as e:
                    return {"error": f"JSON decode error: {str(e)}"}

        # Return the complete result
        return {"response": "".join(result)}
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP request failed: {str(e)}"}

@app.route('/ask', methods=['POST'])
def ask_model():
    """Endpoint to query the model."""
    data = request.json

    # Validate the input JSON
    prompt = data.get("prompt")
    image_path = data.get("image_path", None)

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # Validate the image path (if provided)
    if image_path and not os.path.isabs(image_path):
        # Convert the relative path to absolute
        image_path = os.path.abspath(image_path)

    try:
        response = query_llama_vision(prompt, image_path)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Show the current working directory for debugging
    print(f"Current working directory: {os.getcwd()}")

    app.run(host='0.0.0.0', port=5000, debug=True)  # Enable debug mode
