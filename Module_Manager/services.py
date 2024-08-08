# module_manager/views.py

from django.http import JsonResponse
from django.views import View
from dotenv import load_dotenv
import json
import os
from openai import OpenAI
from Module_Manager.Tasks import Task
from File_Manager.services import FileManager
from LLM_Bottleneck.services import LLM_Bottleneck
from RAG_Manager.services import TechnicalQueryAssistant
from Complaint_Manager.services import ComplaintManager
# Importar otros managers aquí cuando estén disponibles

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ModuleManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.docs = "COA = certificado de calidad = certificado de analisis, IFU = Prospecto , PD = Descripcion de producto = Ficha tecnica, SDS = Hoja de seguridad, CC = Color chart, FDA = Certificado FDA = 510K "
            self.prompt = f"""Eres un asistente que clasifica consultas de usuarios e identifica tareas a realizar. Puede haber multiples tareas en una consulta. \
                    Tu respuesta debe ser un JSON que indique si has recibido una 'fileRequest' (solicitud de documentos), una 'technical_query' (consulta técnica), \
                    un 'complaint' (reclamo) o un 'purchase_opportunity' (consulta de compra).  Los documentos que te puede pedir el usuario son: {self.docs}.\
                    Debes responder únicamente en el siguiente formato JSON: \
                    {{
                        "tasks": [
                            "technical_query" | "fileRequest" | "complaint" | "purchase_opportunity"
                        ]
                    }}"""
            self.tasks = []
           
            self.file_manager = FileManager()
            self.complaint_manager=ComplaintManager()
            self.LLM_BN = LLM_Bottleneck()
         
            self.technical_query_assistant = TechnicalQueryAssistant()
           
            # Inicializar otros managers aquí cuando estén disponibles
            self.current_task = None  # Contexto de la tarea actual
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")
        
    def classify_query(self, query):
        self.query = query
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt}, 
                {"role": "user", "content": f"Clasifica la siguiente consulta y genera el JSON correspondiente: {query}"}
            ]
        )
        classification = response.choices[0].message.content
        classification_json = json.loads(classification)
        for task_type in classification_json["tasks"]:
            print(task_type)
            task = Task(task_type)
            self.tasks.append(task)
        self.process_tasks()
        resp= self.LLM_BN.generate_tasks_response(query)
        
        return resp
     

    def process_tasks(self):
        while self.tasks:
            task = self.tasks[0]  # Obtener la primera tarea sin eliminarla
            if task.state in ['pending', 'in_progress', 'waiting_for_info']:
                self.handle_task(task)
            if task.state == 'completed':
                self.tasks.pop(0)

    def handle_task(self, task):
        if task.task_type == "fileRequest":
            print("Resolviendo solicitud de documentos...")
            self.file_manager.resolve_task(task,self.query)
            print(task.get_response())
            print("llego hasta aca?")

            self.LLM_BN.receive_task(task,)
            print(task.get_response())
            print(type(task.get_response() ))
            # if task.state == 'completed':
            #    print(task.response)  # Esto luego no va, se manda al LLM_Bottleneck.
            # task.update_state('completed')

        elif task.task_type == "technical_query":
            print("Resolviendo consulta técnica...")

            self.technical_query_assistant.handle_technical_query(self.query,task)
            
            self.LLM_BN.receive_task(task)
    
            
        elif task.task_type == "complaint":
            print("Resolviendo reclamo...")
            self.complaint_manager.handle_complaint(self.query,task)
            self.LLM_BN.receive_task(task)
            task.update_state('completed')
            # Lógica para resolver reclamo
        elif task.task_type == "purchase_opportunity":
            print("Resolviendo oportunidad de compra...")
            task.update_state('completed')
            # Lógica para resolver oportunidad de compra
        else:
            print(f"Tarea desconocida: {task.task_type}")
            if task.state == 'completed':
                self.tasks.pop(0)  # Eliminar la tarea completada
        