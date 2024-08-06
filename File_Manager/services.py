# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse
from Module_Manager.Tasks import Task
from File_Manager import SubTask
import json
import os


class FileManager:
    def __init__(self):
        try:
            self.prompt_extract_parameters = None
            self.products = None
            self.document_types = None
            self.prompt_gather_parameters = None
            self.historial = []
            
       
        except Exception as e:
            print( JsonResponse({'error': f"An error occurred while creating atributes: {str(e)}"}, status=500))
        response = self.load_data()
        if isinstance(response, JsonResponse):
            print(response.content.decode())  # Puedes manejar la respuesta de error según sea necesario

    def load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path) as f:
                data = json.load(f)
                self.prompt_extract_parameters = data.get("prompt_extract_parameters")
                self.products = data.get("products")
                self.document_types = data.get("document_types")
                self.prompt_gather_parameters = data.get("prompt_gather_parameters")
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
            return None
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
    
    def agregar_mensaje(self, rol, contenido):
        self.historial.append({"role": rol, "content": contenido})

    def get_file_parameters(self, query):
        self.agregar_mensaje("user", query)
       
        response = OpenAI.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.historial,
            user=self.hilo_id
        )
        respuesta = response.choices[0].message.content
        self.agregar_mensaje("assistant", respuesta)
        return respuesta


    def resolve_task(self,task):
       ST=SubTask('IFU')
       ST.set_response("Aca va la logica para crear las subtareas y resolverlas")
       task.add_subtask(ST)
       task.update_state('completed') 

       
        


    # def classify_query(self, query):
    #     response = self.client.chat.completions.create(
    #         model="gpt-4o-mini",
    #         messages=[
    #             {"role": "system", "content": self.prompt}, 
    #             {"role": "user", "content": f"Clasifica la siguiente consulta y genera el JSON correspondiente: {query}"}
    #         ]
    #     )
    #     classification = response.choices[0].message.content
    #     classification_json = json.loads(classification)
    #     for task_type in classification_json["tasks"]:
    #         task = Task(task_type)
    #         self.tasks.append(task)
