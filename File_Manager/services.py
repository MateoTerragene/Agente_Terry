# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse
from Module_Manager.Tasks import Task
from File_Manager.SubTask import FMSubTask
import json
import os
import difflib

import re
from .handlers.get_ifu_file import get_ifu_file
from .handlers.get_coa_file import get_coa_file

class FileManager:
    def __init__(self):
        try:
            self.prompt_extract_parameters = None
            self.products = None
            self.document_types = None
            self.prompt_gather_parameters = None
            self.historial = []
            self.tasks=[]
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.document_types_string = ""
            self.products_string = ""
            self.prompt = None  
            self.assistant_id = os.getenv('FILE_MANAGER_ASSISTANT_ID')
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return  

            self.prompt = f"Eres un experto en la extracción de información de conversaciones. Extrae las variables importantes y devuélvelas en formato JSON, únicamente cuando hayas extraído toda la información requerida para cada tipo de documento. Para los Certificates of Analysis (COA), extrae el PRODUCT y el LOT. Para las Product descriptions or technical data sheet (DP), Safety Data Sheet (SDS), Color Charts (CC) y FDA certificates 510K (FDA), extrae solo el PRODUCT. Devuelve un JSON por CADA documento solicitado solo si se ha extraído toda la información requerida. Tu rol NO es devolver documentos. Documento solo puede ser igual a {self.document_types_string}. Producto solo puede ser igual a {self.products_string}. NO PIDAS CONFIRMACIÓN."
            self.state = {
                "documento": None,
                "producto": None,
                "lote": None
            }

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
    def extract_variables(self, conversation,historial):
        messages = historial + [{"role": "user", "content": str(conversation)}]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": str(conversation)}
            ],
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.5,
        )
        
        # Extrae la respuesta generada por el modelo
        generated_text = response.choices[0].message.content
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
                    
                    task = {
                        "documento": self.state.get("documento"),
                        "producto": self.state.get("producto"),
                        "lote": self.state.get("lote")
                    }
                    
                    for key in task:
                        if key in data and data[key]:
                            task[key] = data[key]
                    
                    self.tasks.append(task)
        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")
            self.state = {
                "documento": None,
                "producto": None,
                "lote": None
            }
            
    def reset_state(self):
        self.state = {
            "documento": None,
            "producto": None,
            "lote": None
        }

    def clear_historial(self):
        self.historial = []

    def best_match(self, nombre_busqueda, lista_productos):
        
        nombre_normalizado = self.limpiar_texto(nombre_busqueda)
        
        lista_normalizada = [self.limpiar_texto(nombre) for nombre in lista_productos]
        
        mejor_coincidencia = difflib.get_close_matches(nombre_normalizado, lista_normalizada, n=1, cutoff=0.0)
        
        if mejor_coincidencia:
           
            indice = lista_normalizada.index(mejor_coincidencia[0])
           
            return lista_productos[indice]
        else:
            return None
        
    def get_file(self):
        file_links = []
        if self.tasks:
            for task in self.tasks:
                document_type = task.get("documento")
                file_link = None
                
                if document_type == "IFU":
                    file_link = get_ifu_file(task)
                elif document_type == "COA":
                    file_link = get_coa_file(task)
                # elif document_type == "DP":
                #     file_link = get_dp_file(task)
                # elif document_type == "SDS":
                #     file_link = get_sds_file(task)
                # elif document_type == "CC":
                #     file_link = get_cc_file(task)
                # elif document_type == "FDA":
                #     file_link = get_fda_file(task)
                else:
                    print(f"Tipo de documento no reconocido: {document_type}")

            if file_link:
                file_links.append(file_link)

        # Concatenar todos los enlaces en una sola cadena, separada por ', '
        files = ', '.join(file_links)

        # Establecer la respuesta del task con la cadena concatenada
        return(files)
    
    def limpiar_texto(self, texto):  #elimina caracteres extraños
        texto=str(texto)
        return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()
        
    
    #####################################################################
    def gather_parameters(self,query,task,thread):
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=query
        
            )
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="assistant", content=self.prompt_gather_parameters
        
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
        task.update_state('in_progress')
        self.historial.append({"role": "user", "content": query})
        response=self.gather_parameters(query,task,thread)
        self.historial.append({"role": "assistant", "content": response})
        parameters = self.extract_variables(query,self.historial)
        self.update_state(parameters)
        file_link = self.get_file()  
        if file_link:                                                                   #si se obtuvo el enlace se concatena en una variable y se cambia el estado de la bandera a 1                   
            response = f" Devuelve el siguiente enlace textual: '{file_link}'" 
            task.update_state('completed') 
            self.reset_state()
            self.clear_historial() 
            print(response)
        task.set_response(response)
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