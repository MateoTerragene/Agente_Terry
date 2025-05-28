# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse
from File_Manager.SubTask import FMSubTask
import json
import os
import re
import time
from .handlers.file_handlers import file_handlers
from File_Manager.models import DocumentRequest
class FileManager:
    def __init__(self):
        try:
            # self.prompt_extract_parameters = None
            self.products = None
            self.document_types = None
            # self.prompt_gather_parameters = None
            self.historial = []
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.document_types
            self.document_types_string = ""
            self.products_string = ""
            self.assistant_id = os.getenv('FILE_MANAGER_ASSISTANT_ID')
            self.file_handler=file_handlers()
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return  
            self.prompt = (
                "Eres un experto en la extracción de información de conversaciones. Extrae las variables importantes y devuélvelas en formato JSON estrictamente válido, "
                "únicamente cuando hayas extraído toda la información requerida para cada tipo de documento. Para los Certificates of Analysis (COA), "
                "extrae el PRODUCT y el LOT. Si el usuario solicita un COA de producto 'IC1020', 'IC1020FR', 'IC1020FRLCD', 'Trazanto', 'MiniBio', 'MiniPro', 'Photon','Hyper' o 'Trazanto' extrae tambien el Numero de serie. Para las Instructions for Use (IFU), Product Description or technical data sheet (DP), Safety Data Sheet (SDS), "
                "Color Charts (CC), FDA certificates 510K (FDA) y Manuales, extrae solo el PRODUCT. Para los certificados ISO DNV(ISO) no se necesitan otras variables. Devuelve un JSON por CADA documento solicitado solo si se ha extraído toda la información requerida. "
                "Retorna 'documento: ','producto: ' y 'lote: ' si es necesario. Siempre devuelve en el mismo idioma que te preguntaron. Tu rol NO es devolver documentos. Documento solo puede ser igual a "
                f"{self.document_types_string}. Producto solo puede ser igual a {self.products_string}. Si no puedes extraer alguna variable, déjala vacía. Si el usuario solicita un COA y quiere el último LOTE disponible, en 'lote' devuelve 'last'. "
                "Utiliza el historial de la conversación para completar cualquier información faltante. NO PIDAS CONFIRMACIÓN. "
                "Asegúrate de que cada par clave-valor en el JSON esté rodeado de comillas dobles, y que las claves estén en minúsculas. "
                "El JSON debe tener la siguiente estructura: "
                "{ 'documento': 'tipo_de_documento', 'producto': 'nombre_del_producto', 'lote': 'numero_de_lote', 'NS'='numero_de_serie' }. "
                "Ejemplo de JSON válido: { 'documento': '', 'producto': '', 'lote': '', 'ns': '' }. "
                "Solo devuelve el JSON puro, sin texto adicional ni explicaciones."
                
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
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.products = data.get("products")
                self.products_string = ", ".join(self.products)
                self.document_types = data.get("document_types")
                self.document_types_string = ", ".join(self.document_types)
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
            return None
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
        
    def extract_variables(self, conversation,thread):
        
        self.historial.append({"role": "user", "content": str(conversation)})
        
        # print(f"historial: {self.historial}")
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt},
                *self.historial
            ],
            max_tokens=200,
            n=1, 
            stop=None,
            temperature=0.5,
        )

        generated_text = response.choices[0].message.content
        print(f"Json generado por -> extract_variables: {generated_text}")
       
        return generated_text

        
    def update_state(self, task, extracted_params):
        try:
            # Registro detallado del contenido recibido
            # print(f"Contenido completo recibido: {extracted_params}")
            
            json_blocks = re.findall(r'\{.*?\}', extracted_params, re.DOTALL)
            # print(f"Bloques JSON identificados: {json_blocks}")
            
            for block in json_blocks:
                # print(f"Procesando bloque JSON: {block}")
                data = json.loads(block)
                self._process_json_item(task, data)

        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {block}")

    def _process_json_item(self, task, data):
        # Crear una instancia de FMSubTask
        fm_subtask = FMSubTask()
        fm_subtask.state = 'in_progress'
        documento=None
        producto=None
        lote=None
        ns=None
        # Verificar si "documento" y "producto" están presentes y son válidos antes de asignarlos
        if data.get("documento"):
            documento = data.get("documento")
        if data.get("producto"):
            producto = data.get("producto")
        if data.get("lote"):
            lote = data.get("lote")
        if data.get("ns"):
            ns = data.get("ns")

        # Solo proceder si "documento" y "producto" son válidos
        if documento in self.document_types:
            fm_subtask.documento = documento    
        if producto in self.products:
            fm_subtask.producto = producto
        if lote:  # "lote" es opcional, por lo que solo se asigna si está presente
            fm_subtask.lote = lote
        if ns:
            fm_subtask.NS=ns   
            # Agregar la subtarea a la lista de subtareas
        task.subtasks.append(fm_subtask)
        print("Subtarea creada y añadida:", fm_subtask)
        

    def clear_historial(self):
        self.historial.clear()

    
        
    def get_file(self, task, user_identifier, thread_id, is_whatsapp=False):
        if not task.subtasks:
            return str(task.response)  # Retorna vacío si no hay subtareas

        first_subtask = task.subtasks[0]
        document = first_subtask.documento
        product = first_subtask.producto
        lot = first_subtask.lote
        ns= first_subtask.NS
        document_handlers = {
            "IFU": lambda: self.file_handler.get_ifu_file(product),
            "COA": lambda: self.file_handler.get_coa_file(product, lot,ns),
            "DP": lambda: self.file_handler.get_dp_file(product),
            "SDS": lambda: self.file_handler.get_sds_file(product),
            "CC": lambda: self.file_handler.get_cc_file(product),
            "FDA": lambda: self.file_handler.get_fda_file(product),
            "ISO": lambda: self.file_handler.get_iso_file(),
            "MANUAL": lambda: self.file_handler.get_user_manual_file(product)
        }

        handler = document_handlers.get(document)

        if handler:
            file_link = handler()
            first_subtask.response = file_link
            first_subtask.state = 'completed'

            # Guardar la solicitud en la base de datos
            DocumentRequest.objects.create(
                user_id=user_identifier if not is_whatsapp else None,
                phone_number=user_identifier if is_whatsapp else None,
                thread_id=thread_id,
                documento=document,
                producto=product,
                lote=lot,
                link=file_link
            )

        else:
            print(f"Tipo de documento no reconocido: {document}")

        return first_subtask.response


    #####################################################################
    def gather_parameters(self, missing_parameters, completed_parameters, thread):
        try:
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
                f"documents can be: {self.document_types_string} and products can be: {self.products_string}. Do not return the list of products unless explicitly requested.."
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
            
            while run.status != 'completed':
                print(f"Run status: {run.status}. Waiting for completion...")
                time.sleep(0.2)  # Pausa de 2 segundos para evitar sobrecargar el servidor
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.thread_id,
                    run_id=run.id
                )
                if run.status == 'failed':
                    print("Error: la ejecución falló.")
                    return None
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
                            print(f"classification gather param: {classification}")
                            return classification
            else:
                print(run.status)
        except Exception as e:
            print(f"Error en gather_parameters: {e}")
            return None        
        
        



    def check_what_is_empty(self,task):
        """
        Verifica qué parámetros faltan y cuáles están completados en la primera subtarea 
        (task.subtasks[0]) y devuelve dos strings: uno con los parámetros vacíos 
        y otro con los parámetros completos, concatenados en formato de cadena.
        """
        missing_parameters = []
        completed_parameters = []

        if task.subtasks:
            first_subtask = task.subtasks[0]

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
                if first_subtask.producto and  first_subtask.producto.upper() in ["IC1020", "IC1020FR", "IC1020FRLCD", "TRAZANTO", "MINIBIO", "MINIPRO", "PHOTON","HYPER" , "TRAZANTO"]: 
                    print("entro a incubadoras")
                    if not first_subtask.NS:
                        missing_parameters.append("Número de serie")
                    else:
                        completed_parameters.append("Número de serie")  
                    
            if first_subtask.documento == "ISO":
                missing_parameters=[]
                
        # Convertir las listas en cadenas de texto
        missing_str = ", ".join(missing_parameters)
        completed_str = ", ".join(completed_parameters)
        
        return missing_str, completed_str
    
    def fill_fields(self,task, parameters):
        """
        Rellena los campos de la primera subtarea (task.subtasks[0]) con los parámetros extraídos,
        siempre que los parámetros estén completos en el JSON recibido.
        """
        documento=None
        producto=None
        lote=None
        ns=None
        try:
            parameters = parameters.replace("'", '"')
            json_data = json.loads(parameters)
            # print(json_data)
            if task.subtasks:
                first_subtask = task.subtasks[0]
            # print("paso el if subtask")
                # Verificar si "documento" y "producto" están presentes y son válidos antes de asignarlos
            if json_data.get("documento"):
                documento = json_data.get("documento")
            if json_data.get("producto"):
                producto = json_data.get("producto")
                # print("producto FF")
                # print(producto)
            if json_data.get("lote"):
                lote = json_data.get("lote")
                
            if json_data.get("ns"):
                ns= json_data.get("ns")

            # Solo proceder si "documento" y "producto" son válidos
            if documento in self.document_types:
                first_subtask.documento = documento    
            if producto in self.products:
                print("producto esta en self.products")
                first_subtask.producto = producto
            if lote:  # "lote" es opcional, por lo que solo se asigna si está presente
                first_subtask.lote = lote
            if ns:
                first_subtask.NS=ns
        except json.JSONDecodeError as e:
            print(f"Error al parsear JSON en fill_fields: {e}")

 ############################################# Nueva Version de Resolve_task ###################################
    def resolve_task(self, query, task, thread, user_identifier, is_whatsapp=False):
        print(f"[DEBUG] Starting resolve_task for task type: {task.task_type}, state: {task.state}")
        print(f"[DEBUG] Initial subtasks: {len(task.subtasks)} subtasks")

        task.response = ""
        if task.state == 'pending':
            messages = self.client.beta.threads.messages.list(thread_id=thread.thread_id).data
            print(f"[DEBUG] Messages retrieved from thread: {len(messages)} messages")

            if len(messages) > 4:
                print("[DEBUG] Adding messages to historial")
                self.historial.append({"role": "user", "content": str(messages[4].content[0].text.value)})
                self.historial.append({"role": "assistant", "content": str(self.client.beta.threads.messages.list(thread_id=thread.thread_id).data[0].content[0].text.value)})

        parameters = self.extract_variables(query, thread)
        print(f"[DEBUG] Extracted parameters: {parameters}")

        if task.state == 'pending':
            print("[DEBUG] Task is pending. Updating state.")
            self.update_state(task, parameters)
            print(f"[DEBUG] State updated. Current subtasks: {len(task.subtasks)}")
            task.update_state()
        else:
            print("[DEBUG] Task is not pending. Filling fields.")
            self.fill_fields(task, parameters)

        index = 0
        while index < len(task.subtasks):
            subtask = task.subtasks[index]
            print(f"[DEBUG] Processing subtask at index {index}: {subtask}")

            missing_str, completed_str = self.check_what_is_empty(task)
            print(f"[DEBUG] Missing parameters: {missing_str}")
            print(f"[DEBUG] Completed parameters: {completed_str}")

            if not missing_str:
                print("[DEBUG] No missing parameters. Getting file.")
                file_link = self.get_file(task, user_identifier, thread.thread_id, is_whatsapp)
                print(f"[DEBUG] File link obtained: {file_link}")

                if task.response:
                    task.response = str(file_link) + ", " + str(task.response)
                else:
                    task.response = str(file_link)

                del task.subtasks[index]
                print(f"[DEBUG] Subtask removed. Remaining subtasks: {len(task.subtasks)}")
            else:
                print("[DEBUG] Missing parameters detected. Gathering additional information.")
                generated_question = self.gather_parameters(missing_str, completed_str, thread)
                print(f"[DEBUG] Generated question: {generated_question}")
                self.clear_historial()
                task.response = str(generated_question) + ", " + str(task.response)
                break

        task.update_state()
        print(f"[DEBUG] Task state after processing subtasks: {task.state}")

        if task.state != 'completed':
            missing_parameters, completed_parameters = self.check_what_is_empty(task)
            print(f"[DEBUG] Missing parameters: {missing_parameters}, Completed parameters: {completed_parameters}")

            generated_question = self.gather_parameters(missing_parameters, completed_parameters, thread)
            print(f"[DEBUG] Generated follow-up question: {generated_question}")
            self.clear_historial()
            task.response = str(generated_question) + ", " + str(task.response)

        self.historial.append({"role": "assistant", "content": task.response})
        if task.state == 'completed':
            print("[DEBUG] Task completed. Clearing historial.")
            self.clear_historial()

        task.set_response(task.response)
        print(f"[DEBUG] Final task response: {task.response}")
