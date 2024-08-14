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
                "extrae el PRODUCT y el LOT. Para las Instructions for Use (IFU), Product Description or technical data sheet (DP), Safety Data Sheet (SDS), "
                "Color Charts (CC) y FDA certificates 510K (FDA), extrae solo el PRODUCT. Para los certificados ISO DNV(ISO) no se necesitan otras variables. Devuelve un JSON por CADA documento solicitado solo si se ha extraído toda la información requerida. "
                "Retorna 'documento: ','producto: ' y 'lote: ' si es necesario. Tu rol NO es devolver documentos. Documento solo puede ser igual a "
                f"{self.document_types_string}. Producto solo puede ser igual a {self.products_string}. Si no puedes extraer alguna variable dejala vacia. Si el usuario solicita un COA y quiere el ultimo LOTE disponible, en 'lote' devuelve 'last' "
                "Utiliza el historial de la conversación para completar cualquier información faltante. NO PIDAS CONFIRMACIÓN."
                "{ 'documento': '','producto':'','lote':''}"
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
            # Separar múltiples bloques de "JSON" (que en realidad son diccionarios de Python)
            json_blocks = extracted_params.split('}\n{')
            
            # Ajustar los bloques para que sean JSON válidos
            json_blocks = [
                '{' + block + '}' if not block.startswith('{') and not block.endswith('}') else 
                '{' + block if not block.startswith('{') else 
                block + '}' if not block.endswith('}') else 
                block
                for block in json_blocks
            ]
            
            for block in json_blocks:
                # Reemplazar comillas simples con comillas dobles para hacer el bloque un JSON válido
                cleaned_params = block.strip().replace("'", '"')
                
                if cleaned_params:
                    # Convertir la cadena JSON a un objeto Python
                    data = json.loads(cleaned_params)
                    
                    # Procesar cada bloque JSON
                    self._process_json_item(data)

        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")



    def _process_json_item(self, data):
        # Crear una instancia de FMSubTask
        fm_subtask = FMSubTask()
        fm_subtask.state = 'in_progress'
        documento=None
        producto=None
        lote=None
        # Verificar si "documento" y "producto" están presentes y son válidos antes de asignarlos
        if data.get("documento"):
            documento = data.get("documento")
        if data.get("producto"):
            producto = data.get("producto")
        if data.get("lote"):
            lote = data.get("lote")

        # Solo proceder si "documento" y "producto" son válidos
        if documento in self.document_types:
            fm_subtask.documento = documento    
        if producto in self.products:
            fm_subtask.producto = producto
        if lote:  # "lote" es opcional, por lo que solo se asigna si está presente
            fm_subtask.lote = lote
            
            # Agregar la subtarea a la lista de subtareas
        self.task.subtasks.append(fm_subtask)
        print("Subtarea creada y añadida:", fm_subtask)
        

            


    def clear_historial(self):
        self.historial = []

    
        
    def get_file(self):
        # self.task.response = ""

        if not self.task.subtasks:
            return self.task.response  # Retorna vacío si no hay subtareas

        first_subtask = self.task.subtasks[0]
        document = first_subtask.documento
        product = first_subtask.producto
        lot = first_subtask.lote

        # Procesar según el tipo de documento
        if document == "IFU":
            first_subtask.response = self.file_handler.get_ifu_file(product)
            first_subtask.state = 'completed'

        elif document == "COA":
            first_subtask.response = self.file_handler.get_coa_file(product, lot)
            first_subtask.state = 'completed'

        elif document == "DP":
            first_subtask.response = self.file_handler.get_dp_file(product)
            first_subtask.state = 'completed'

        elif document == "SDS":
            first_subtask.response = self.file_handler.get_sds_file(product)
            first_subtask.state = 'completed'

        elif document == "CC":
            first_subtask.response = self.file_handler.get_cc_file(product)
            first_subtask.state = 'completed'

        elif document == "FDA":
            first_subtask.response = self.file_handler.get_fda_file(product)
            first_subtask.state = 'completed'
        elif document == "ISO":
            first_subtask.response = self.file_handler.get_iso_file()
            first_subtask.state = 'completed'
        else:
            print(f"Tipo de documento no reconocido: {document}")

        # Acumular la respuesta en task.response
        # if first_subtask.response:
        #     self.task.response = first_subtask.response
        # print("respuesta de get_file")
        # print(self.task.response)
        # Retornar la respuesta acumulada
        return first_subtask.response


    #####################################################################
    def gather_parameters(self, missing_parameters, completed_parameters, thread):
        # Crear el contenido del mensaje del usuario basado en lo que ya se ha proporcionado y lo que falta
        user_content = (
            f"He proporcionado los siguientes detalles: {completed_parameters}. "
            # f"Pero aún necesito proporcionar: {missing_parameters}."
        )

        # Enviar el mensaje del usuario
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user", content=user_content
        )

        # Crear el contenido del mensaje del asistente para guiar al usuario
        assistant_content = (
            "You are an AI Product Specialist Assistant. Your primary role is to gather the specific parameters required for different document types based on user requests. "
            "The user has already provided some details: "
            f"{completed_parameters}. "
            "Now, you need to gather the remaining information: "
            f"{missing_parameters}. "
            "Please request these missing parameters from the user in a clear and concise manner. Remember: Your task is strictly to gather and provide the necessary parameters, not to deliver documents or provide technical assistance."
            f"documents can be: {self.document_types_string} and products can be: {self.products_string}."
        )

        # Enviar el mensaje del asistente
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="assistant", content=assistant_content
        )

        # Ejecutar el run del asistente y esperar la respuesta
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.thread_id,
            assistant_id=self.assistant_id,
        )

        if run.status == 'completed':
            messages_response = self.client.beta.threads.messages.list(
                thread_id=thread.thread_id
            )
            messages = messages_response.data
            latest_message = messages[0]

            if messages and hasattr(latest_message, 'content'):
                content_blocks = latest_message.content
                if isinstance(content_blocks, list) and len(content_blocks) > 0:
                    text_block = content_blocks[0]
                    if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                        classification = text_block.text.value
                        return classification
        else:
            print(run.status)

        return None
        



    def check_what_is_empty(self):
        """
        Verifica qué parámetros faltan y cuáles están completados en la primera subtarea 
        (self.task.subtasks[0]) y devuelve dos strings: uno con los parámetros vacíos 
        y otro con los parámetros completos, concatenados en formato de cadena.
        """
        missing_parameters = []
        completed_parameters = []

        if self.task.subtasks:
            first_subtask = self.task.subtasks[0]

            if not first_subtask.documento:
                missing_parameters.append("documento")
            else:
                completed_parameters.append("documento")
            
            if not first_subtask.producto:
                missing_parameters.append("producto")
            else:
                completed_parameters.append("producto")
            
            if first_subtask.documento == "COA":
                if not first_subtask.lote:
                    missing_parameters.append("lote")
                else:
                    completed_parameters.append("lote")
            if first_subtask.documento == "ISO":
                missing_parameters=[]
                
        # Convertir las listas en cadenas de texto
        missing_str = ", ".join(missing_parameters)
        completed_str = ", ".join(completed_parameters)
        
        return missing_str, completed_str
    
    def fill_fields(self, parameters):
        """
        Rellena los campos de la primera subtarea (self.task.subtasks[0]) con los parámetros extraídos,
        siempre que los parámetros estén completos en el JSON recibido.
        """
        documento=None
        producto=None
        lote=None
        try:
            parameters = parameters.replace("'", '"')
            json_data = json.loads(parameters)
            print(json_data)
            if self.task.subtasks:
                first_subtask = self.task.subtasks[0]
            print("paso el if subtask")
                # Verificar si "documento" y "producto" están presentes y son válidos antes de asignarlos
            if json_data.get("documento"):
                documento = json_data.get("documento")
            if json_data.get("producto"):
                producto = json_data.get("producto")
                print("producto FF")
                print(producto)
            if json_data.get("lote"):
                lote = json_data.get("lote")

            # Solo proceder si "documento" y "producto" son válidos
            if documento in self.document_types:
                first_subtask.documento = documento    
            if producto in self.products:
                first_subtask.producto = producto
            if lote:  # "lote" es opcional, por lo que solo se asigna si está presente
                first_subtask.lote = lote

        except json.JSONDecodeError as e:
            print(f"Error al parsear JSON en fill_fields: {e}")

 ############################################# Nueva Version de Resolve_task ###################################
    def resolve_task(self, query, task, thread):
        self.task.response=""
        self.task = task
        parameters = self.extract_variables(query, self.historial)
        
        # Verificar si no hay subtareas y actualizar el estado si es necesario
        if task.state=='pending':
            self.update_state(parameters)
            print(f"creo la subtask:{self.task.subtasks}")
            self.task.update_state()
            task.update_state(self.task.state)
        else:
            # Llenar los campos de la primera subtarea con los parámetros extraídos
            self.fill_fields(parameters)
            print("entro al else")

        
            

        index = 0
        while index < len(self.task.subtasks):
            subtask = self.task.subtasks[index]
            missing_str, completed_str = self.check_what_is_empty()
            print("missing parameters: ")
            print(missing_str)
            print("completed param")
            print(completed_str)

            if not missing_str:
                file_link = self.get_file()
                if self.task.response:
                    self.task.response = str(file_link) + ", " + str(self.task.response)
                else:
                    self.task.response = str(file_link)

                
                del self.task.subtasks[index]
                # No incrementas el índice porque la lista se acorta
            else:
                index += 1  # Solo incrementas si no se elimina nada

        self.task.update_state()
        print(self.task.update_state())
        task.update_state(self.task.state)                

        if task.state!='completed' :
            # Verificar qué parámetros están vacíos y cuáles están completos
            missing_parameters, completed_parameters = self.check_what_is_empty()

            # Generar la pregunta para recopilar los parámetros que faltan
            generated_question = self.gather_parameters(missing_parameters, completed_parameters,thread)

            # Construir la respuesta final
            self.task.response = str(generated_question) + ", " + str(self.task.response)
        self.clear_historial()
        # Establecer la respuesta en la tarea
        print(f"response: {self.task.response}")
        task.set_response(self.task.response)
        
        
 ########################################################################
    # def handle_file_request(self,query,task,thread):
    # def resolve_task(self,query,task,thread):    
    #     self.task=task
    #     task.update_state('in_progress')
    #     self.historial.append({"role": "user", "content": query})
    #     response=self.gather_parameters(query,task,thread)
    #     self.historial.append({"role": "assistant", "content": response})
    #     parameters = self.extract_variables(query,self.historial)
    #     self.update_state(parameters)
    #     file_link = self.get_file()
    #     task.update_state()
       
    #     # print("estado de la task al final de resolve_task")
    #     # print(self.task.get_state())  
    #                                                     #si se obtuvo el enlace se concatena en una variable y se cambia el estado de la bandera a 1                   
    #     response = file_link + ", " + response 
            
    #     self.clear_historial() 
            
    #     task.set_response(response)
    #     # print(response)
        
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