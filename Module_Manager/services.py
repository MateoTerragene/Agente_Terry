# module_manager/views.py
import copy
import logging

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
from PO_Manager.services import PurchaseOpportunity

# Importar otros managers aquí cuando estén disponibles
logger = logging.getLogger(__name__)
load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ModuleManager:
    def __init__(self):
        try:
            print("ADENTRO DEL CONSTRUCTOR")
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
            # self.task = Task()
            self.file_manager = FileManager()
            self.complaint_manager=ComplaintManager()
            self.PO_manager = PurchaseOpportunity()
            
         
            self.technical_query_assistant = TechnicalQueryAssistant()
            self.LLM_BN = LLM_Bottleneck()
            # Inicializar otros managers aquí cuando estén disponibles
            # self.current_task = None  # Contexto de la tarea actual
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")
        
    def classify_query(self, thread, query):
        thread_id = thread.thread_id
        print(f"ClassQuer Usando el thread ID: {thread_id} para clasificar la consulta.")
        logger.info(f"Usando el thread ID: {thread_id} para clasificar la consulta.")
        self.query = query
        if not self.tasks or self.tasks[0].get_state() == 'pending':
            print("entro a clasificar")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.prompt}, 
                    {"role": "user", "content": f"Clasifica la siguiente consulta y genera el JSON correspondiente: {query}"}
                ]
                # thread_id=thread_id  # Asegúrate de que el thread_id es el correcto
            )
            classification = response.choices[0].message.content
            classification_json = json.loads(classification)
            for task_type in classification_json["tasks"]:
                task = Task()  # Crear una nueva instancia de Task (o la clase que estés utilizando)
                task.set_type(task_type)
                print(task.task_type)
                self.tasks.append(task)
            # self.task = copy.deepcopy(self.tasks[0])
            
        self.process_tasks(thread)
        resp= self.LLM_BN.generate_tasks_response(query)
        
        return resp
     

    def process_tasks(self,thread):
       
        for i in range(len(self.tasks)):
            task = self.tasks[0]  # Siempre obtenemos la primera tarea

            self.handle_task(task,thread)

            if task.get_state() == 'completed':
                self.tasks.pop(0)  # Eliminar la tarea completada de la lista

         
    def handle_task(self,task,thread):
        if task.task_type == "fileRequest":
            print("Resolviendo solicitud de documentos...")
            self.file_manager.resolve_task(task,self.query)
           
            self.LLM_BN.receive_task(task.clone())
 

        elif task.task_type == "technical_query":
            print("Resolviendo consulta técnica...")

            self.technical_query_assistant.handle_technical_query(self.query,task,thread)
           
            self.LLM_BN.receive_task(task.clone())
    
            
        elif task.task_type == "complaint":
            print("Resolviendo reclamo...")
            self.complaint_manager.handle_complaint(self.query,task,thread)
           
            self.LLM_BN.receive_task(task.clone())
            # task.update_state('completed')
            # Lógica para resolver reclamo


        elif task.task_type == "purchase_opportunity":
            print("Resolviendo oportunidad de compra...")
            self.PO_manager.resolve_task(task,self.query)
           
            self.LLM_BN.receive_task(task.clone())
 
        else:
            print(f"Tarea desconocida: {task.task_type}")
            if task.state == 'completed':
                self.tasks.pop(0)  # Eliminar la tarea completada
        