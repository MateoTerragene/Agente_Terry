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
                "You are an assistant that helps to organize and summarize responses from various tasks. "
                "Your job is to take the responses from different tasks, provided by the user, and generate "
                "a coherent and well-formatted summary. Do not send the user Query, send only the answer (do not specify that it is the answer). Additionally, you can rephrase sentences to make them "
                "clearer and more elegant."
            )
            self.tasks = []
            self.task_responses = ""
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

    def generate_response(self, user_prompt):             # Esta funcion se puede llamar dentro de una funcion que saque una respuesta por el chat
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        classification = response.choices[0].message.content
        return classification

    def generate_tasks_response(self, query):      #esta funcion deberia llamarse al final de Module_Manager/services classify_query
        user_prompt = self.generate_prompt_tasks(query)
        response = self.generate_response(user_prompt)
        # print(response) # este print es solo para probar
        print(response)
        return response

    def receive_task(self, task):        # esta funcion deberia llamarse al final de cada "if  y elif" de Module_Manager/services handle_task 
        self.tasks.append(task)

 