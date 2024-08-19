import os
import re
from openai import OpenAI
from Module_Manager import Tasks
from django.http import JsonResponse
import json
class LLM_Bottleneck:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.abort_signal=False
            self.prompt = (
                "I am an assistant designed to merge and organize the responses provided to me. "
                "My role is to combine the responses from various tasks given by the user into a cohesive and well-structured summary. "
                "If I receive an empty string or if a query is presented without any accompanying information, I will not provide a response. "
                "I will only output a merged summary of the information provided, rephrasing sentences if necessary to improve clarity and elegance. "
                "I will respond in the first person, using a natural and conversational tone, and I will not return the user query—only the answer, without specifying that it is the answer. "
                "I will detect the language of the query and always respond in the same language unless explicitly asked to switch languages. "
                "If I do not understand the query or do not have enough information to generate a response, I will simply ask for more details."
                "If it is the first message greet the user as Terry, the AI expert in biotechnology. Only greet the user on the first messages, do not greet the user on the rest of the messages"
                "If I detect any explicit intention to end the conversation or abort the task in the user input, I will return the sequence '#-#-#-#-#-#-', inform the user that the task has been aborted and was not completed, and make myself available for further assistance. "
                )
            # "If I detect any explicit intention to end the conversation or abort the task in the user input, I will return the sequence '#-#-#-#-#-#-', inform the user that the task has been aborted and was not completed, and make myself available for further assistance. "
            
            self.tasks = []
            # self.task_responses = ""
            self.assistant_id = os.getenv('LLM_BOTTLENECK_ASSISTANT_ID')
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
    def generate_prompt_tasks(self, query):  

        for task in self.tasks:
            print(f"task responsesdentreo de generate prompt: {task.get_response()}")
        # esta funcion nunca se llama, solamente dentro de generate_tasks_response
        responses = ". ".join([task.get_response() for task in self.tasks])
        user_prompt = f"Query: {query}, Responses: {responses}"
        return user_prompt

    def generate_response(self, user_prompt,thread):             # Esta funcion se puede llamar dentro de una funcion que saque una respuesta por el chat
      
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=user_prompt
        
            )
        print(f"LLM_BN user prompt: {user_prompt}")
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
                    
                                                
        print(f"classification dentro de generate_response: {classification}")
        return classification
    def detect_abort_signal(self, response):
        pattern = r"(#-)+"
        if re.search(pattern, response):
            self.abort_signal = True ### SOLO PARA PROBAR
        
            # Eliminar el patrón de response
            cleaned_response = re.sub(pattern, "", response)
            return cleaned_response.strip()
        else:
            self.abort_signal = False
            return response
    
    def generate_tasks_response(self, query,thread):      #esta funcion deberia llamarse al final de Module_Manager/services classify_query
        response=""
        user_prompt = self.generate_prompt_tasks(query)
        print(f"response antes de generarla: {response}")
        response = self.generate_response(user_prompt,thread)
        
        print(f"abort signal antes de detectar: {self.abort_signal}")
        print(f"response antes de detectar: {response}")
        response= self.detect_abort_signal(response)
        # print(response) # este print es solo para probar
        # print(response)
        self.tasks.clear()
        print("  ")
        print(f"abort signal despues de detectar: {self.abort_signal}")
        print("******************************************************************************")
        print("Respuesta: LLM_Bottleneck -> generate response:  ")
        print(response)
        print("******************************************************************************")
        return response

    def receive_task(self, task):        # esta funcion deberia llamarse al final de cada "if  y elif" de Module_Manager/services handle_task 
        self.tasks.append(task)

 