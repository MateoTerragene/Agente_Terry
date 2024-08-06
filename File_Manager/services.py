# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse

import json
import os


class FileManager:
    def __init__(self):
        self.prompt_extract_parameters = None
        self.products = None
        self.document_types = None
        self.prompt_gather_parameters = None
        self.historial = []

        response = self.load_data()
        if isinstance(response, JsonResponse):
            print(response)  # Maneja la respuesta de error según sea necesario

    def load_data(self):
        try:
            with open('data.json') as f:
                data = json.load(f)
                self.prompt_extract_parameters = data["prompt_extract_parameters"]
                self.products = data["products"]
                self.document_types = data["document_types"]
                self.prompt_gather_parameters = data["prompt_gather_parameters"]
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=501)
    def agregar_mensaje(self, rol, contenido):
        self.historial.append({"role": rol, "content": contenido})

    def get_file_parameters(self, query):
        self.agregar_mensaje("user", query)
        self.agregar_mensaje("system", "Eres el asistente 1.")
        response = OpenAI.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.historial,
            user=self.hilo_id
        )
        respuesta = response.choices[0].message.content
        self.agregar_mensaje("assistant", respuesta)
        return respuesta


    def resolve_task(self):
        "Aca va la logica para crear las subtareas y resolverlas"
        


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

    def resolve_task():
        "Aca va la logica para crear las subtareas y resolverlas"
        return(0)
