from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()  # Load environment variables from .env file

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')

    def handle_technical_query(self, query,task,thread):
        task.update_state('in_progress')
        # Make the call to the chat completions endpoint with the assistant ID and ensure it uses the vector store
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=f"{query}"
           
        )



        run = self.client.beta.threads.runs.create(
            thread_id=chat.thread_id,
            assistant_id=self.assistant_id,
            tool_choice="auto")
        print(f"Run Created: {run.id}")

        while run.status != "completed":
            run = self.client.beta.threads.runs.retrieve(thread_id=thread.thread_id,run_id=run.id)
            print(f"Run Status: {run.status}")
            if run.status == "failed":
                break
            time.sleep(0.5)
        
        if run.status != "failed":
            print("Run Completed!")

            messages_response = self.client.beta.threads.messages.list(thread_id=thread.thread_id)
            messages = messages_response.data
            latest_message = messages[0]
####################lo agregue para sacar el resultado en un str
            if messages and hasattr(latest_message, 'content'):
                content_blocks = messages[0].content
                if isinstance(content_blocks, list) and len(content_blocks) > 0:
                    text_block = content_blocks[0]
                    if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                        text_value = text_block.text.value
                        print("************************************************************************")
                        print("respuesta RAG: ")
                        print(text_value)
                        print("************************************************************************")
                        task.set_response(text_value)
                        task.update_state('completed')
                        
                   
            # return f"Response: {latest_message.content[0].text.value}"