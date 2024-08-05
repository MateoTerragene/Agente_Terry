from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()  # Load environment variables from .env file

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')

    def handle_technical_query(self, query):
        # Make the call to the chat completions endpoint with the assistant ID and ensure it uses the vector store
        chat = self.client.beta.threads.create(
            messages=[
                {
                    "role":"user",
                    "content":f"{query}"
                }
            ]
        )



        run = self.client.beta.threads.runs.create(
            thread_id=chat.id,
            assistant_id=self.assistant_id,
            tool_choice="auto")
        print(f"Run Created: {run.id}")

        while run.status != "completed":
            run = self.client.beta.threads.runs.retrieve(thread_id=chat.id,run_id=run.id)
            print(f"Run Status: {run.status}")
            if run.status == "failed":
                break
            time.sleep(0.5)
        
        if run.status != "failed":
            print("Run Completed!")

            messages_response = self.client.beta.threads.messages.list(thread_id=chat.id)
            messages = messages_response.data

            latest_message = messages[0]
            return f"Response: {latest_message.content[0].text.value}"