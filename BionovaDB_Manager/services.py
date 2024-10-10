import os
import json
import boto3
from openai import OpenAI
import time
from dotenv import load_dotenv


load_dotenv()  
class BionovaDBManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION')
            )
            self.bucket_name = os.getenv('S3_BUCKET_NAME')  # Añadir el nombre del bucket aquí
            
            
            self.assistant_id = os.getenv('BIONOVA_DB_MANAGER_ASSISTANT_ID')
            
        except Exception as e:
            print(f"Error al inicializar ImageManager: {e}")

    def get_presigned_url(self, s3_key, expiration=3600):
        """
        Genera una URL firmada para acceder temporalmente a un archivo en S3.
        
        Args:
            s3_key (str): Clave del archivo en S3.
            expiration (int): Tiempo de expiración en segundos (por defecto 1 hora).
        
        Returns:
            str: URL firmada para acceder al archivo.
        """
        try:
            print(f"Generating presigned URL for key: {s3_key} in bucket: {self.bucket_name}")  # Print para ver el s3_key y el bucket
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            print(f"Presigned URL generated: {response}")  # Print para ver la URL generada
            return response
        except Exception as e:
            print(f"Error al generar la URL firmada: {e}")
            return None

    def clear_pass(self, s3_db_path):
        """
        Limpia la contraseña
        """
        try:
            
            return 'En el siguiente enlace encontraras la data base blanqueada: db_blanqueada'

        except json.JSONDecodeError as json_err:
            print(f"Error al parsear la respuesta a JSON: {json_err}")
            return None
        except Exception as e:
            print(f"Error al analizar la imagen con OpenAI: {e}")
            return None

    def handle_Bionova_DB(self,query, task,  thread):
        try:
            task.update_state('in_progress')
            print(f"query en dbmanager: {query}")
            if 'https://agente-terry.s3.amazonaws.com/db/' in query:
                print("entro al if de dbmanager")
                task.response=self.clear_pass(query)
                task.state = 'completed'
            # Actualizar el estado de la tarea
            else:

                # Enviar la consulta al endpoint de OpenAI threads.messages
                chat = self.client.beta.threads.messages.create(
                    thread_id=thread.thread_id,
                    role="user", content=f"{query}"
                )
                
                # Crear una nueva ejecución en OpenAI
                run = self.client.beta.threads.runs.create(
                    thread_id=chat.thread_id,
                    assistant_id=self.assistant_id,
                    tool_choice="auto"
                )
                print(f"Run Created: {run.id}")
                
                # Esperar a que la ejecución se complete
                while run.status != "completed":
                    run = self.client.beta.threads.runs.retrieve(thread_id=thread.thread_id, run_id=run.id)
                    print(f"Run Status: {run.status}")
                    if run.status == "failed":
                        print("Error: la ejecución falló.")
                        break
                    time.sleep(0.5)
                
                if run.status != "failed":
                    print("Run Completed!")
                    
                    # Obtener los mensajes recientes
                    messages_response = self.client.beta.threads.messages.list(thread_id=thread.thread_id)
                    messages = messages_response.data
                    latest_message = messages[0]
                    
                    # Extraer el texto del mensaje
                    if messages and hasattr(latest_message, 'content'):
                        content_blocks = latest_message.content
                        if isinstance(content_blocks, list) and len(content_blocks) > 0:
                            text_block = content_blocks[0]
                            if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                                text_value = text_block.text.value
                                print("Texto extraído:", text_value)
                                task.set_response(text_value)
                                task.update_state('completed')
                else:
                    print("La ejecución falló. No se pudo completar el proceso.")
            
        except AttributeError as e:
            print(f"Error de atributo: {e}")
            
        except Exception as e:
            print(f"Error general: {e}")
