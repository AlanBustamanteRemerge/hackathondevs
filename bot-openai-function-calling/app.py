from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import subprocess
import logging
from openai import AsyncOpenAI
import json

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

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

if not OPENAI_API_KEY:
    raise ValueError("Failed to retrieve OpenAI API key")


# SQLite database configuration
db_file = "example.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Insert example data
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    price REAL
)
""")
conn.commit()

# Insert example data
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Laptop", 999.99))
cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Mouse", 19.99))
conn.commit()

# Initialize FastAPI
app = FastAPI()

# Model to validate the request body
class QueryRequest(BaseModel):
    query: str

# Predefined function to retrieve data from the database
def get_product_info(product_name: str):
    cursor.execute("SELECT name, price FROM products WHERE name = ?", (product_name,))
    result = cursor.fetchone()
    if result:
        return {"name": result[0], "price": result[1]}
    else:
        return {"error": "Product not found"}

# Define the function for GPT
functions = [
    {
        "name": "get_product_info",
        "description": "Retrieve product information from the database",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "The name of the product to look up"
                }
            },
            "required": ["product_name"]
        }
    }
]

@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        # Request GPT to process the query
        response = await client.chat.completions.create(
            model="gpt-4-0613",
            messages=[{"role": "user", "content": request.query}],
            functions=functions,
            function_call="auto"
        )

        # Direct access to the attributes of response.choices
        if response.choices and response.choices[0].message.function_call:
            function_name = response.choices[0].message.function_call.name
            arguments = response.choices[0].message.function_call.arguments

            if function_name == "get_product_info":
                args = json.loads(arguments)
                result = get_product_info(args["product_name"])
                return {"result": result}

        # General response
        return {"response": response.choices[0].message.content}

    except Exception as e:
        logging.error(f"Error during OpenAI API call: {e}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
