# module_manager/services.py
import time
import logging
from dotenv import load_dotenv
import json
import os
from openai import OpenAI
from Module_Manager.Tasks import Task
from File_Manager.services import FileManager
from LLM_Bottleneck.services import LLM_Bottleneck
from RAG_Manager.services import TechnicalQueryAssistant
from Form_Manager.services import FormManager
from PO_Manager.services import PurchaseOpportunity
from BionovaDB_Manager.services import BionovaDBManager
from Image_Manager.services import ImageManager
# Importar otros managers aquí cuando estén disponibles
logger = logging.getLogger(__name__)
load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ModuleManager:
    def __init__(self):
        try:
            # print("ADENTRO DEL CONSTRUCTOR")
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.docs = "COA = certificado de calidad = certificado de analisis, IFU = Prospecto , PD = Descripcion de producto = Ficha tecnica, SDS = Hoja de seguridad, CC = Color chart, FDA = Certificado FDA = 510K "
            self.prompt = f"""
            Eres un asistente que clasifica consultas de usuarios, identifica tareas a realizar y optimiza las consultas para que sean más claras y efectivas. Puede haber múltiples tareas en una consulta.

            ### Clasificación de tareas
            Tu respuesta debe ser un JSON que indique lo siguiente:
            1. Las tareas detectadas en la consulta. Estas pueden ser:
            - "technical_query" (consulta técnica)
            - "fileRequest" (solicitud de documentos)
            - "form" (intención de convertirse en distribuidor de Terragene)
            - "image_submission" (recepción de imagen)
            - "clear_DB" (blanqueo de contraseña).

            2. La consulta traducida al inglés y optimizada según estas pautas:
            - Analiza la consulta para identificar conceptos clave e intención.
            - Identifica términos ambiguos y sugiere sinónimos o aclaraciones.
            - Considera términos relacionados, sinónimos y frases alternativas para mejorar la búsqueda.
            - Expande siglas o abreviaturas si es aplicable.
            - Incorpora cualquier contexto relevante o conocimiento específico del dominio.
            - Asegúrate de que la consulta optimizada mantenga la intención original del usuario.
            - Prioriza claridad y especificidad en la consulta optimizada.
            - Si la consulta original ya es óptima, simplemente tradúcela al inglés sin cambios.

            3. El idioma original de la consulta como un nombre de idioma (por ejemplo, 'Spanish', 'English', 'French').

            Los documentos que te puede pedir el usuario son: {self.docs}.
            Si recibes algo que contenga 'https://agente-terry.s3.amazonaws.com/images/', clasifícalo como 'image_submission'.
            Si recibes algo que contenga 'https://agente-terry.s3.amazonaws.com/db/', clasifícalo como 'clear_DB'.

            ### Formato de salida
            Debes responder únicamente en el siguiente formato JSON:
            {{
                "tasks": [
                    "technical_query" | "fileRequest" | "form" | "image_submission" | "clear_DB"
                ],
                "query_translation": {{
                    "translated_query": "consulta traducida y optimizada en inglés",
                    "original_language": "idioma original"
                }}
            }}
            """
                # - "purchase_opportunity" (oportunidad de compra) \
                # | "purchase_opportunity"  # Comentado: esta tarea ya no es relevante
            self.tasks = []
            # self.task = Task()
            self.file_manager = FileManager()
            self.form_manager=FormManager()
            self.PO_manager = PurchaseOpportunity()
            self.image_manager = ImageManager()
         
            self.technical_query_assistant = TechnicalQueryAssistant()
            self.LLM_BN = LLM_Bottleneck()
            self.DB_manager=BionovaDBManager()
            # Inicializar otros managers aquí cuando estén disponibles
            # self.current_task = None  # Contexto de la tarea actual
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")

    def reset_tasks(self):
        """Limpia las tareas y marca la primera como completada si existe."""
        # if self.tasks:
        #     self.tasks[0].set_state('completed')  # Marcar la primera tarea como completada
        self.tasks.clear()  # Limpia la lista de tareas          
    def classify_query(self, thread, query, user_identifier, is_whatsapp=False):
        start_time = time.time()
        try:
            thread_id = thread.thread_id
            print(f"[DEBUG] Thread ID: {thread_id}")
            logger.info(f"Usando el thread ID: {thread_id} para clasificar la consulta.")
            self.query = query
            print(f"[DEBUG] Initial query: {self.query}")

            if self.LLM_BN.abort_signal:
                print("[DEBUG] Abort signal detected. Clearing tasks.")
                self.LLM_BN.abort_signal = False
                self.tasks.clear()

            if not self.tasks or self.tasks[0].get_state() == 'pending':
                # print("[DEBUG] Entering classification block.")
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.prompt}, 
                        {"role": "user", "content": f"Clasifica la siguiente consulta y genera el JSON correspondiente: {query}"}
                    ]
                )
                try:
                    classification = response.choices[0].message.content
                    print(f"[DEBUG] Classification response: {classification}")
                    classification_json = json.loads(classification)
                    # print(f"[DEBUG] Parsed classification JSON: {classification_json}")

                    tasks = classification_json.get("tasks", [])
                    # print(f"[DEBUG] Tasks extracted: {tasks}")

                    if not tasks:
                        # print("[DEBUG] No tasks detected in classification.")
                        thread.language = classification_json.get("query_translation", {}).get("original_language", "Unknown")
                        thread.save()  # Guarda el idioma detectado en el thread
                        response = self.LLM_BN.generate_tasks_response(query, thread, thread.language)
                        return response, None

                    for task_type in tasks:
                        task = Task()
                        task.set_type(task_type)
                        self.tasks.append(task)
                        # print(f"[DEBUG] Task added: {task.task_type}")

                    # print(f"[DEBUG] All tasks: {[task.task_type for task in self.tasks]}")

                    query_translation = classification_json.get("query_translation", {})
                    translated_query = query_translation.get("translated_query")
                    original_language = query_translation.get("original_language")
                    # print(f"[DEBUG] Query translation: {query_translation}")

                    # Almacenar el idioma únicamente en el thread
                    thread.language = original_language if original_language else "Unknown"
                    thread.save()

                    self.query = translated_query if translated_query else self.query
                    # print(f"[DEBUG] Final query after translation: {self.query}")

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[ERROR] Error al procesar la clasificación: {e}")
                    return "Classification error", None

            # print(f"[DEBUG] Tasks before processing: {[task.task_type for task in self.tasks]}")
            completed_task_type = self.process_tasks(thread, user_identifier, is_whatsapp)
            # print(f"[DEBUG] Completed task type: {completed_task_type}")

            # Usar el idioma desde el thread
            resp = self.LLM_BN.generate_tasks_response(self.query, thread, thread.language)

            print(f"[DEBUG] Response from LLM_Bottleneck: {resp}")
            return resp, completed_task_type

        except Exception as e:
            logger.error(f"Error in classify_query: {e}")
            print(f"[ERROR] Exception in classify_query: {e}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            print(f"[DEBUG] classify_query completed in {elapsed_time:.2f} seconds")


    def process_tasks(self, thread, user_identifier, is_whatsapp=False):
        start_time = time.time()
        try:
            for i in range(len(self.tasks)):
                # task = self.tasks[0]  # Siempre obtenemos la primera tarea

                self.handle_task(thread, user_identifier, is_whatsapp)
                # print("estado task dentro de process_task")
                # print(task.get_state())
                if self.tasks[0].get_state() == 'completed':
                    completed_task_type = self.tasks[0].task_type
                    self.tasks.pop(0)  # Eliminar la tarea completada de la lista
                    return completed_task_type
            return None 
        except Exception as e:
            logger.error(f"Error in process_tasks: {e}")
            raise
        finally:
            total_elapsed = time.time() - start_time
            print(f"process_tasks completed in {total_elapsed:.2f} seconds")
            
    def handle_task(self, thread, user_identifier, is_whatsapp=False):
        if self.tasks[0].task_type == "fileRequest":
            print("Resolviendo solicitud de documentos...")
            self.file_manager.resolve_task(self.query,self.tasks[0],thread,user_identifier, is_whatsapp)
            # print("estado de la task FM")
            # print(task.get_state())
            self.LLM_BN.receive_task(self.tasks[0].clone())
 

        elif self.tasks[0].task_type == "technical_query":
            print("Resolviendo consulta técnica...")

            self.technical_query_assistant.handle_technical_query(self.query,self.tasks[0],thread)
           
            self.LLM_BN.receive_task(self.tasks[0].clone())
    
            
        elif self.tasks[0].task_type == "form":
            print("Resolviendo Form...")
            self.form_manager.handle_form(self.query,self.tasks[0],thread)
           
            self.LLM_BN.receive_task(self.tasks[0].clone())
            # task.update_state('completed')
            # Lógica para resolver reclamo


        elif self.tasks[0].task_type == "purchase_opportunity":
            print("Resolviendo oportunidad de compra...")
            
            self.PO_manager.resolve_task(self.tasks[0],self.query)
            self.LLM_BN.receive_task(self.tasks[0].clone())
        
        elif self.tasks[0].task_type == "image_submission":
            print("Resolviendo recepción de imagen...")
            self.image_manager.process_image(self.tasks[0],self.query,thread)
           
            self.LLM_BN.receive_task(self.tasks[0].clone())
            
        elif self.tasks[0].task_type == "clear_DB":
            print("Resolviendo blanqueo de clave...")

            self.DB_manager.handle_Bionova_DB(self.query,self.tasks[0],user_identifier, thread)
           
            self.LLM_BN.receive_task(self.tasks[0].clone())

        else:
            print(f"Tarea desconocida: {self.tasks[0].task_type}")
            if self.tasks[0].state == 'completed':
                self.tasks.pop(0)  # Eliminar la tarea completada

