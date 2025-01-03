import hashlib
import os
import boto3
import sqlite3
import subprocess
from dotenv import load_dotenv
import requests
import shutil
from openai import OpenAI
load_dotenv()

class BionovaDBManager:
    def __init__(self):
        try:
            self.bdstr = 'a7ZEyiDhJt'  # Contraseña de cifrado
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION')
            )
            self.bucket_name = os.getenv('S3_BUCKET_NAME')  # Nombre del bucket de S3
            
            self.db_path = None
            self.assistant_id = os.getenv('BIONOVA_DB_MANAGER_ASSISTANT_ID')
        except Exception as e:
            print(f"Error al inicializar BionovaDBManager: {e}")

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
            # print(f"Generating presigned URL for key: {s3_key} in bucket: {self.bucket_name}")  # Print para ver el s3_key y el bucket
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
    




    def download_db(self, url):
        """Descarga la base de datos desde una URL firmada en S3."""
        print(f"Intentando descargar la base de datos desde la URL: {url}")

        try:
            response = requests.get(url, stream=True)
            
            # Imprimir información detallada sobre la respuesta
            print(f"Estado de la respuesta HTTP: {response.status_code}")
            print(f"Encabezados de la respuesta: {response.headers}")
            
            if response.status_code == 200:
                print("Respuesta exitosa, descargando el archivo...")
                
                # Garantizar que tmp/ existe
                os.makedirs('tmp', exist_ok=True)

                # Guardar el archivo en tmp/
                self.db_path = os.path.join('tmp', 'downloaded_db.db')
                print(f"Guardando el archivo en la ruta local: {self.db_path}")
                
                with open(self.db_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                    
                print(f"Base de datos descargada correctamente: {self.db_path}")
            else:
                print(f"Error al descargar la base de datos, código de estado: {response.status_code}")
                print(f"Contenido de la respuesta: {response.text}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud de descarga: {e}")
        except Exception as e:
            print(f"Error al descargar la base de datos: {e}")



    def clear_pass(self, s3_db_path, task, user_identifier, thread):
        """Limpia la contraseña de la base de datos ejecutando comandos Pascal."""
        try:
            if not self.bucket_name:
                print("Error: 'bucket_name' no está configurado. Verifica las variables de entorno.")
                return "Error: 'bucket_name' no configurado."

            # Extraer clave S3 y generar URL firmada
            if s3_db_path.startswith(f"https://{self.bucket_name}.s3.amazonaws.com/"):
                s3_key = s3_db_path[len(f"https://{self.bucket_name}.s3.amazonaws.com/"):]
                url = self.get_presigned_url(s3_key)
                if url:
                    # Garantizar que tmp/ existe
                    os.makedirs('tmp', exist_ok=True)

                    # Guardar archivo en tmp/ con el mismo nombre que en S3
                    self.db_path = os.path.join('tmp', os.path.basename(s3_key))
                    self.download_db(url)
                else:
                    print("Error: No se pudo generar la URL firmada.")
                    return "Error: No se pudo generar la URL firmada."
            else:
                print("Error: La URL proporcionada no coincide con el bucket.")
                return "Error: La URL proporcionada no coincide con el bucket."

            # Verificar si el archivo existe
            if not os.path.exists(self.db_path):
                print(f"Error: El archivo dentro de clear_pass {self.db_path} no existe.")
                return "Error: Archivo no encontrado."

            # Comandos disponibles
            commands = ["open", "decrypt", "reset", "encrypt"]
            # commands = ["open", "reset"]
            results = []

            # Ejecutar cada comando
            executable_path = os.path.join('BionovaDB_Manager', 'BioReset')
            for command in commands:
                try:
                    print(f"Ejecutando comando '{command}'...")
                    result = subprocess.run(
                        [executable_path, command, self.db_path],
                        text=True,  # Capturar salida como texto
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True  # Lanza excepción en caso de error
                    )
                    print(f"Comando '{command}' ejecutado correctamente.")
                    print(f"Salida: {result.stdout.strip()}")
                    print("-" * 50)  # Separador entre comandos
                except subprocess.CalledProcessError as e:
                    print(f"Error al ejecutar el comando '{command}'.")
                    print(f"Mensaje de error: {e.stderr.strip()}")
                    print("-" * 50)  # Separador en caso de error

                # Retornar resultados acumulados
                return "\n".join(results)

        except Exception as e:
            print(f"Error inesperado en clear_pass: {e}")
            return f"Error inesperado: {str(e)}"


    def handle_Bionova_DB(self, query, task, user_identifier, thread):
        """Maneja las tareas relacionadas con la base de datos Bionova."""
        try:
            task.update_state('in_progress')
            print(f"Query en dbmanager: {query}")
            if 'https://agente-terry.s3.amazonaws.com/db/' in query:
                # print("Entrando en el if de dbmanager")
                task.response = self.clear_pass(query,task, user_identifier, thread)
                task.state = 'completed'
            else:
                # Aquí podrías manejar consultas generales, como en el ejemplo anterior.
                pass

        except Exception as e:
            print(f"Error general: {e}")
