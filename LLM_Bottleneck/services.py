# llm_bottleneck/services.py
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
                "My role is to combine responses from various tasks into a cohesive and well-structured summary. "
                "I will rephrase sentences if necessary for clarity and elegance, responding in the first person with a natural, conversational tone. "
                "I will not include the user query in my response—only the answer. I will detect the query's language at the user prompt and answer in the same language, unless explicitly asked to switch. Do not consider 'Responses' language."
                "If a query lacks accompanying information or is empty, I will not respond. "
                "If I do not understand the query or need more information, I will ask for more details. "
                "On the first message, I will greet the user as Terry, the AI expert in biotechnology, but I will not greet the user in subsequent messages. "
                "I will always return a JSON object that contains two fields: "
                "1. 'response': a string with the final answer, "
                "2. 'abort': a boolean value indicating whether the task should be aborted (True or False). "
                "I will detect common phrases or keywords that suggest the user wants to stop, such as 'stop', 'abort', 'end', 'cancel', 'no more', 'I regret' or 'that's it'. "
                "If I detect this, I will set the 'abort' field to True. "
                "If there is no intention to abort, I will set 'abort' to False. "
                "An empty response does NOT indicate an abort signal. Please respond accordingly."
                        )
            
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

        # for task in self.tasks:
        #     print(f"task responsesdentreo de generate prompt: {task.get_response()}")
        # esta funcion nunca se llama, solamente dentro de generate_tasks_response
        responses = ". ".join([task.get_response() for task in self.tasks])
        user_prompt = f"Query: {query}, Responses: {responses}"
        # print(f"user_prompt: {user_prompt}")
        return user_prompt

    def generate_response(self, user_prompt, thread):
        try:
            # Envía el mensaje del usuario
            self.client.beta.threads.messages.create(
                thread_id=thread.thread_id,
                role="user",
                content=user_prompt
            )
            
            # Envía el prompt
            self.client.beta.threads.messages.create(
                thread_id=thread.thread_id,
                role="assistant",
                content=self.prompt
            )
            
            # Ejecuta y espera la respuesta del asistente
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.thread_id,
                assistant_id=self.assistant_id,
            )
            
            if run.status == 'completed':
                # Recupera los mensajes de la conversación
                messages_response = self.client.beta.threads.messages.list(thread_id=thread.thread_id)
                messages = messages_response.data
                latest_message = messages[0] if messages else None
                
                # Verifica si existe contenido en el mensaje más reciente
                if latest_message and hasattr(latest_message, 'content'):
                    content_blocks = latest_message.content
                    if isinstance(content_blocks, list) and len(content_blocks) > 0:
                        text_block = content_blocks[0]
                        
                        if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                            classification = text_block.text.value
                            
                            # Imprimir el contenido crudo para inspección
                            # print(f"Raw classification content: {classification}")
                            
                            # Intenta parsear el JSON devuelto por el modelo
                            try:
                                response_json = json.loads(classification)
                                # print(f"response_json: {response_json}")
                                
                                # Verifica que el JSON contiene los campos esperados
                                if 'response' in response_json and 'abort' in response_json:
                                    response = response_json.get('response')
                                    self.abort_signal = response_json.get('abort')
                                    # print(f"respuesta en generate_response: {response}")
                                    return response
                                else:
                                    # Devuelve un error si el formato no es el esperado
                                    return {'error': 'Invalid response format'}
                            
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}")
                                return {'error': 'Response is not a valid JSON'}
                else:
                    return {'error': 'No content found in latest message'}
            else:
                print(f"Run status: {run.status}")
                return {'error': f'Run did not complete, status: {run.status}'}
        
        except Exception as e:
            print(f"Exception in generate_response: {e}")
            return {'error': f'Unexpected error: {str(e)}'}


            

    
    def generate_tasks_response(self, query,thread):      #esta funcion deberia llamarse al final de Module_Manager/services classify_query
        response=""
        user_prompt = self.generate_prompt_tasks(query)
        response = self.generate_response(user_prompt,thread)
        self.tasks.clear()

        
        print("******************************************************************************")
        print(f"abort signal: {self.abort_signal}")
        print("Respuesta del LLM_Bottleneck:  ")
        print(response)
        print("******************************************************************************")
        return response

    def receive_task(self, task):        # esta funcion deberia llamarse al final de cada "if  y elif" de Module_Manager/services handle_task 
        self.tasks.append(task)

 