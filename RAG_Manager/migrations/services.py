from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def handle_technical_query(self, query):
        # Ejemplo de cómo podrías realizar la llamada a la base de datos vectorial de OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente técnico con acceso a una base de datos vectorial."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content