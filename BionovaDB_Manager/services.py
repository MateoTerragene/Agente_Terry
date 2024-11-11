import hashlib
import os
import boto3
import sqlite3
from pysqlcipher3 import dbapi2 as sqlite
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
    
    def hash_string(self, msg: str) -> str:
        """Genera un hash SHA-256 de un string y lo retorna como hexadecimal."""
        return hashlib.sha256(msg.encode()).hexdigest().lower()

    def cifrar(self):
        """Cifra la base de datos con la contraseña original."""
        try:
            password = self.hash_string(self.bdstr)
            con = sqlite.connect(self.db_path)
            con.execute(f"ATTACH DATABASE '{self.db_path}' AS encrypted KEY '{password}'")
            con.execute(f"PRAGMA rekey = '{password}'")
            con.commit()
            con.close()
            print("Base de datos cifrada correctamente.")
        except Exception as e:
            print(f"Error al intentar cifrar la base de datos: {e}")

    def descifrar(self):
        """Descifra la base de datos utilizando la contraseña original."""
        try:
            password = self.hash_string(self.bdstr)
            con = sqlite.connect(self.db_path)
            con.execute(f"ATTACH DATABASE '{self.db_path}' AS encrypted KEY '{password}'")
            con.execute("PRAGMA rekey = ''")  # Restablece la clave para descifrar
            con.commit()
            con.close()
            print("Base de datos descifrada correctamente.")
        except Exception as e:
            print(f"Error al intentar descifrar la base de datos: {e}")
    


    def download_db(self, url):
        """Descarga la base de datos desde una URL firmada en S3."""
        print(f"Intentando descargar la base de datos desde la URL: {url}")  # Imprimir la URL que estamos usando

        try:
            response = requests.get(url, stream=True)
            
            # Imprimir información detallada sobre la respuesta
            print(f"Estado de la respuesta HTTP: {response.status_code}")  # Mostrar el código de estado HTTP
            print(f"Encabezados de la respuesta: {response.headers}")  # Imprimir los encabezados para ver si hay algo relevante
            
            if response.status_code == 200:
                print("Respuesta exitosa, descargando el archivo...")
                
                # Definir una ruta local para almacenar la base de datos
                self.db_path = 'downloaded_db.db'
                print(f"Guardando el archivo en la ruta local: {self.db_path}")
                
                with open(self.db_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                    
                print(f"Base de datos descargada correctamente: {self.db_path}")
            else:
                print(f"Error al descargar la base de datos, código de estado: {response.status_code}")
                # Imprimir el contenido de la respuesta para más detalles si no es 200
                print(f"Contenido de la respuesta: {response.text}")
            
        except requests.exceptions.RequestException as e:
            # Manejar errores específicos de requests
            print(f"Error en la solicitud de descarga: {e}")
        except Exception as e:
            # Capturar cualquier otro error
            print(f"Error al descargar la base de datos: {e}")


    def clear_pass(self, s3_db_path, task, user_identifier, thread):
        """Limpia la contraseña de la base de datos."""
        try:
            if not self.bucket_name:
                print("Error: 'bucket_name' no está configurado. Verifica las variables de entorno.")
                task.response = "Error: 'bucket_name' no está configurado."
                task.state = 'completed'
                return

            # Extract S3 key from the URL
            try:
                if s3_db_path.startswith(f"https://{self.bucket_name}.s3.amazonaws.com/"):
                    s3_key = s3_db_path[len(f"https://{self.bucket_name}.s3.amazonaws.com/"):]
                else:
                    print("Error: La URL proporcionada no coincide con el bucket.")
                    task.response = "Error: La URL proporcionada no coincide con el bucket."
                    task.state = 'completed'
                    return
            except Exception as e:
                print(f"Error al extraer la clave S3 de la URL: {e}")
                task.response = "Error al procesar la URL de la imagen."
                task.state = 'completed'
                return

            print(f"Processing image with S3 key: {s3_key}")
            try:
                # Obtener la URL firmada para la base de datos en S3
                db_presigned_url = self.get_presigned_url(s3_key)
                if not db_presigned_url:
                    return "Error al obtener la URL de la base de datos en S3."
                
                # Descargar la base de datos desde S3
                self.download_db(db_presigned_url)
                
                # Primero, desciframos la base de datos usando la contraseña original
                self.descifrar()

                # Abrimos la base de datos descifrada y realizamos el cambio de la contraseña
                con = sqlite.connect(self.db_path)
                cursor = con.cursor()
                cursor.execute("UPDATE USERS SET password='admin', reset_pwd=0 WHERE id=1")
                con.commit()  # Guardar los cambios
                con.close()
                print("Contraseña blanqueada correctamente. Se estableció 'admin' para el usuario con ID=1.")
                
                # Ahora, volvemos a cifrar la base de datos con la contraseña original
                self.cifrar()
                
                return "Contraseña blanqueada con éxito."
            except sqlite3.Error as e:
                print(f"Error al procesar la base de datos: {e}")
                return f"Error al procesar la base de datos: {e}"
            except Exception as e:
                print(f"Error inesperado: {e}")
                return f"Error inesperado: {e}"
        except Exception as e:
            print(f"Error general en process_image: {e}")
            task.response = "Error inesperado al procesar la imagen."
            task.state = 'completed'
    def handle_Bionova_DB(self, query, task, user_identifier, thread):
        """Maneja las tareas relacionadas con la base de datos Bionova."""
        try:
            task.update_state('in_progress')
            print(f"Query en dbmanager: {query}")
            if 'https://agente-terry.s3.amazonaws.com/db/' in query:
                print("Entrando en el if de dbmanager")
                task.response = self.clear_pass(query,task, user_identifier, thread)
                task.state = 'completed'
            else:
                # Aquí podrías manejar consultas generales, como en el ejemplo anterior.
                pass

        except Exception as e:
            print(f"Error general: {e}")
