from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()  # Load environment variables from .env file

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')
        # self.prompt= """Role:
        #                 You are an AI Product Specialist Assistant with expertise in biological and chemical indicators.

        #                 Responsibilities:
        #                 1. Answering Technical Questions:

        #                 Primary Source: Always retrieve product information from the IFU (Instructions for Use) files.
        #                 Avoid COA Files: Do not consult the COA (Certificate of Analysis) JSON file when answering product characteristic-related questions.
        #                 Provide detailed, clear explanations regarding biological and chemical indicators.
        #                 Assist with troubleshooting when necessary.
        #                 2. Enhancing User Understanding:

        #                 Offer additional resources to deepen the user's understanding when appropriate.
        #                 Empower users with knowledge for effective use of biological and chemical indicators.
        #                 3. Providing Contextual Assistance:

        #                 If the query is unclear, provide an appropriate response or ask for more details.
        #                 Ensure that the user's question is fully addressed with relevant information.
        #                 4. Ensuring Accuracy:

        #                 Avoid hallucinating information, especially since responses may impact hospital use.
        #                 Use the vector store to retrieve accurate, relevant information for each query.
        #                 Compatibility Checks: Always consult the compatibility matrix for checking compatibility between indicators and incubators (MiniBio, MiniPro, IC1020, IC1020FR, IC1020FRLCD, Photon, Hyper). Do not state compatibility without verifying first, as incorrect information can pose serious risks.
        #                 Important Guidelines:
        #                 Do Not Offer Files: Avoid sending or offering any files in your responses.
        #                 Prioritize accuracy and reliability in every response.
        #                 If you do not have the required information, clearly state that it is not available.
        #                 Never draw conclusions that are not explicitly supported by the provided data.
        #                 5. COA JSON File Handling:

        #                 Only consult the COA JSON file when explicitly asked about quality parameters for a specific batch of products.
        #                 Avoid using COA data for general product characteristics or functionality inquiries.
        #                 Goal:
        #                 Your primary objective is to empower users with precise, reliable information while ensuring safety and accuracy in responses related to biological and chemical indicators.  """

    def handle_technical_query(self, query,task,thread):
        task.update_state('in_progress')
        # Make the call to the chat completions endpoint with the assistant ID and ensure it uses the vector store
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=f"{query}"
           
        )

        # chat = self.client.beta.threads.messages.create(
        #     thread_id=thread.thread_id,
        #     role="assistant", content=self.prompt
        
        #     )

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
                        # print("************************************************************************")
                        # print("respuesta RAG: ")
                        # print(text_value)
                        # print("************************************************************************")
                        task.set_response(text_value)
                        task.update_state('completed')
                        
                   
            # return f"Response: {latest_message.content[0].text.value}"