# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse
from Module_Manager.Tasks import Task
from File_Manager.SubTask import FMSubTask
import json
import os


import re

from .handlers.file_handlers import file_handlers

class FileManager:
    def __init__(self):
        try:
            self.prompt_extract_parameters = None
            self.products = None
            self.document_types = None
            self.prompt_gather_parameters = None
            self.historial = []
            self.task=Task()
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.document_types
            self.document_types_string = ""
            self.products
            self.products_string = ""
            self.prompt = None  
            self.assistant_id = os.getenv('FILE_MANAGER_ASSISTANT_ID')
            self.file_handler=file_handlers()
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return  
            self.prompt = (
                "Eres un experto en la extracción de información de conversaciones. Extrae las variables importantes y devuélvelas en formato JSON, "
                "únicamente cuando hayas extraído toda la información requerida para cada tipo de documento. Para los Certificates of Analysis (COA), "
                "extrae el PRODUCT y el LOT. Para las Instructions for Use (IFU), Product descriptions or technical data sheet (DP), Safety Data Sheet (SDS), "
                "Color Charts (CC) y FDA certificates 510K (FDA), extrae solo el PRODUCT. Devuelve un JSON por CADA documento solicitado solo si se ha extraído toda la información requerida. "
                "Retorna 'documento: ','producto: ' y 'lote: ' si es necesario. Tu rol NO es devolver documentos. Documento solo puede ser igual a "
                f"{self.document_types_string}. Producto solo puede ser igual a {self.products_string}. Si no puedes extraer alguna variable dejala vacia. "
                "Utiliza el historial de la conversación para completar cualquier información faltante. NO PIDAS CONFIRMACIÓN."
            )
            # self.state = {
            #     "documento": None,
            #     "producto": None,
            #     "lote": None
            # }

        except Exception as e:
            print(JsonResponse({'error': f"An error occurred while creating attributes: {str(e)}"}, status=500))
    def load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path) as f:
                data = json.load(f)
                self.prompt_extract_parameters = data.get("prompt_extract_parameters")
                self.products = data.get("products")
                self.products_string = ", ".join(self.products)
                self.document_types = data.get("document_types")
                self.document_types_string = ", ".join(self.document_types)
                self.prompt_gather_parameters = data.get("prompt_gather_parameters")
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
            return None
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
        
    def extract_variables(self, conversation, historial):
        messages = historial + [{"role": "user", "content": str(conversation)}]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt},
                *messages  # Incluye todo el historial y la nueva consulta
            ],
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.5,
        )
        
        # Extrae la respuesta generada por el modelo
        generated_text = response.choices[0].message.content
        print("Json generado por -> extract_variables: ")
        print(generated_text)
        return generated_text

    
    def update_state(self, extracted_params): 
        try:
            # Separar múltiples bloques de JSON
            json_blocks = extracted_params.split('```json')
            
            for block in json_blocks:
                cleaned_params = block.strip().strip('```').strip()
                if cleaned_params:
                    data = json.loads(cleaned_params)
                    
                    # Crear una instancia de FMSubTask
                    fm_subtask = FMSubTask()
                    
                    # Asignar los valores extraídos a los atributos de la instancia
                    fm_subtask.documento = data.get("documento")
                    fm_subtask.producto = data.get("producto")
                    fm_subtask.lote = data.get("lote")
                    
                    # # Verificar si los valores son válidos antes de añadir la tarea
                    # if fm_subtask.documento in self.document_types and fm_subtask.producto in self.products:
                    #     self.tasks.append(fm_subtask)
                    # else:
                    #     print(f"Valores inválidos: documento='{fm_subtask.documento}', producto='{fm_subtask.producto}'")
                    self.task.subtasks.append(fm_subtask)         
            print("self.tasks adentro del update_state: ")
            print(self.task.subtasks)

        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")

                        # # Verificar que 'documento' y 'producto' estén en los conjuntos permitidos
                        # if task["documento"] in self.document_types and task["producto"] in self.products:
                        #     self.tasks.append(task)
                        # else:
                        #     print(f"El documento '{task['documento']}' o el producto '{task['producto']}' no son válidos.")
                        
        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")
            # self.state = {
            #     "documento": None,
            #     "producto": None,
            #     "lote": None
            # }
            
    def reset_state(self):
        # self.state = {
        #     "documento": None,
        #     "producto": None,
        #     "lote": None
        # }
        return 0

    def clear_historial(self):
        self.historial = []

    
        
    def get_file(self):
        self.task.response = ""
        indices_to_remove = []

        for index, subtask in enumerate(self.task.subtasks):
            print("Tratando esta subtask:")
            print(subtask)
            print("*************")
            
            # Acceder a los atributos de la instancia FMSubTask
            document = subtask.documento
            product = subtask.producto
            
            state = 0
            if document == "IFU":
                state, subtask.response = self.file_handler.get_ifu_file(product)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            elif document == "COA":
                lot = subtask.lote  # Acceder al atributo 'lote'
                state, subtask.response = self.file_handler.get_coa_file(product, lot)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            elif document == "DP":
                state, subtask.response = self.file_handler.get_dp_file(product)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            elif document == "SDS":
                state, subtask.response = self.file_handler.get_sds_file(product)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            elif document == "CC":
                state, subtask.response = self.file_handler.get_cc_file(product)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            elif document == "FDA":
                state, subtask.response = self.file_handler.get_fda_file(product)
                if state == 1:
                    subtask.state = 'completed'
                    indices_to_remove.append(index)
            else:
                print(f"Tipo de documento no reconocido: {document}")
            
            # Acumular la respuesta en task.response
            if subtask.response:
                self.task.response += subtask.response

        # Eliminar las subtasks completadas de self.task.subtasks
        for index in sorted(indices_to_remove, reverse=True):
            del self.task.subtasks[index]

        # Retornar la respuesta acumulada
        return self.task.response



        

    

        
    
    #####################################################################
    def gather_parameters(self,query,task,thread):
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=query
        
            )
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="assistant", content="You are an AI Product Specialist Assistant. Your primary role is to gather the specific parameters required for different document types based on user requests. Guidelines: COA (Certificates of Analysis): Gather both PRODUCT and LOT. DP (Product Descriptions/Technical Data Sheets): Gather only the PRODUCT . IFU (Instructions for use / prospecto): Gather only the PRODUCT. SDS (Safety Data Sheets): Gather only the PRODUCT. CC (Color Charts): Gather only the PRODUCT. FDA (510K Certificates): Gather only the PRODUCT. Important Notes: Do not return the documents themselves. Your task is strictly to gather and provide the necessary parameters. If the query is unclear or does not explicitly request a file, respond appropriately or ask the user for more specific details. Remember: Delivering documents is handled by another assistant. Your responsibility is solely to gather the required parameters for each document type. You are prohibited from asking for confirmation of the provided data. You are prohibited from answering technical or any other type of questions."
            # self.prompt_gather_parameters
        
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
    
    # def handle_file_request(self,query,task,thread):
    def resolve_task(self,query,task,thread):    
        self.task=task
        task.update_state('in_progress')
        self.historial.append({"role": "user", "content": query})
        response=self.gather_parameters(query,task,thread)
        self.historial.append({"role": "assistant", "content": response})
        parameters = self.extract_variables(query,self.historial)
        self.update_state(parameters)
        file_link = self.get_file()
        task.update_state()
       
        print("estado de la task al final de resolve_task")
        print(self.task.get_state())  
                                                        #si se obtuvo el enlace se concatena en una variable y se cambia el estado de la bandera a 1                   
        response = file_link + ", " + response 
            
        self.clear_historial() 
            
        task.set_response(response)
        print(response)
        
    #####################################################################################
    # def resolve_task(self,task,entry):
    #     task.update_state('in_progress')
    #     self.load_data()
    #     ST=FMSubTask('IFU')
    #     parameters = self.extract_variables(entry)
    #     self.update_state(parameters)
    #     file_link = self.get_file()                                             #se obtiene el enlace del doc
    #     if file_link:                                                                   #si se obtuvo el enlace se concatena en una variable y se cambia el estado de la bandera a 1                   
    #         additional_context = f" Devuelve el siguiente enlace textual: '{file_link}'" 
    #         Bandera=1
    #     else: 
    #         additional_context = ""
    #     # print(additional_context)
    #     task.add_subtask(ST)
    #     ST.set_response(additional_context)
    #     task.set_response(additional_context)
    #     task.update_state('completed') 
    #     ST.update_state('completed') 
    #     self.reset_state()