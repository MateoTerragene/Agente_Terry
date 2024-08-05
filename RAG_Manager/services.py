from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')

    def handle_technical_query(self, query):
        # Make the call to the chat completions endpoint with the assistant ID and ensure it uses the vector store
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical assistant with access to a vector store for retrieving relevant information."},
                {"role": "user", "content": query}
            ],
            tools=[
                {"type": "file_search"}  # Ensure the retrieval tool is specified
            ]
        )
        return response.choices[0].message.content