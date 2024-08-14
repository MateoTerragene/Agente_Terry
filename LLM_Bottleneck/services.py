import os
from openai import OpenAI
from Module_Manager import Tasks
from django.http import JsonResponse
import json
class LLM_Bottleneck:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.prompt = (
                "I am an assistant designed to merge and organize the responses provided to me. "
                "My role is to combine the responses from various tasks given by the user into a cohesive and well-structured summary. "
                "If I receive an empty string or if a query is presented without any accompanying information, I will not provide a response. "
                "I will only output a merged summary of the information provided, rephrasing sentences if necessary to improve clarity and elegance. "
                "I will respond in the first person, using a natural and conversational tone, and I will not return the user query—only the answer, without specifying that it is the answer. "
                "I will detect the language of the query and always respond in the same language unless explicitly asked to switch languages. "
                "If I do not understand the query or do not have enough information to generate a response, I will simply ask for more details."
            )
            self.tasks = []
            self.task_responses = ""
            self.assistant_id = os.getenv('LLM_BOTTLENECK_ASSISTANT_ID')
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
    def generate_prompt_tasks(self, query):             # esta funcion nunca se llama, solamente dentro de generate_tasks_response
        responses = ". ".join([task.get_response() for task in self.tasks])
        user_prompt = f"Query: {query}, Responses: {responses}"
        return user_prompt

    def generate_response(self, user_prompt,thread):             # Esta funcion se puede llamar dentro de una funcion que saque una respuesta por el chat
        # response = self.client.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": self.prompt},
        #         {"role": "user", "content": user_prompt}
        #     ]
        # )
        # classification = response.choices[0].message.content
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=user_prompt
        
            )
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="assistant", content=self.prompt
        
            )
        run = self.client.beta.threads.runs.create_and_poll(
        thread_id=thread.thread_id,
        assistant_id=self.assistant_id,
        )
        if run.status == 'completed': 
            messages_response = self.client.beta.threads.messages.list(
                thread_id=thread.thread_id                     )
        else:
            print(run.status)
        messages = messages_response.data
        latest_message = messages[0]    
        if messages and hasattr(latest_message, 'content'):
            content_blocks = messages[0].content
            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                text_block = content_blocks[0]
                if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                    classification=   text_block.text.value
                    
                                                
    
        return classification

    def generate_tasks_response(self, query,thread):      #esta funcion deberia llamarse al final de Module_Manager/services classify_query
        user_prompt = self.generate_prompt_tasks(query)
        response = self.generate_response(user_prompt,thread)
        # print(response) # este print es solo para probar
        # print(response)
        self.tasks.clear()
        print("  ")
        print("******************************************************************************")
        print("Respuesta: LLM_Bottleneck -> generate response:  ")
        print(response)
        print("******************************************************************************")
        return response

    def receive_task(self, task):        # esta funcion deberia llamarse al final de cada "if  y elif" de Module_Manager/services handle_task 
        self.tasks.append(task)

 