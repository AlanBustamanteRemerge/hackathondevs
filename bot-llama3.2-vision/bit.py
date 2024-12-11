import base64

# Ruta de la imagen
image_path = "/Users/alan.bustamante/bot-llama3.2-vision/image.jpg"

# Leer y codificar la imagen en base64
with open(image_path, "rb") as f:
    base64_data = base64.b64encode(f.read()).decode("utf-8")
    print(base64_data)  # Imprime el resultado para usarlo en el comando curl
