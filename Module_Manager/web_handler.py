from .file_handler import FileHandler
from django.http import JsonResponse
import logging
import os
import time
import boto3
import subprocess
logger = logging.getLogger(__name__)

class WebHandler:

    def __init__(self):
        self.file_handler = FileHandler()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = 'agente-terry'  # Asegúrate de reemplazar esto por el nombre de tu bucket
    def handle_text_message(self, message, user_id, module_manager, thread):
        """
        Maneja un mensaje de texto enviado desde la web.
        """
        try:
            response, task_type = self.file_handler.handle_text(thread, message, user_id, module_manager,is_whatsapp=False)
            # print(f"response dentro de web_handler: {response}")
            return response, task_type

        except Exception as e:
            logger.error(f"Text message handling error: {str(e)}")
            return JsonResponse({'error': f"Error en el manejo del mensaje de texto: {str(e)}"}, status=500)

    def handle_audio_message(self, file, user_id, module_manager, thread):
        audio_path = None
        processed_audio_path = None
        try:
            # Obtén la extensión del archivo
            file_extension = os.path.splitext(file.name)[1]
            audio_path = f"tmp/{user_id}_{int(time.time())}{file_extension}"
            print(f"Ruta temporal del audio: {audio_path}")
            
            # Guarda el archivo de audio
            with open(audio_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            logger.info(f"Archivo de audio guardado temporalmente en {audio_path}")
            
            # Acondicionar el audio usando FFmpeg
            processed_audio_path = f"tmp/{user_id}_{int(time.time())}_processed.wav"
            command = [
                "ffmpeg",
                "-i", audio_path,
                "-ar", "16000",
                "-ac", "1",
                processed_audio_path
            ]

            try:
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    logger.error(f"Error al procesar el audio: {result.stderr.decode()}")
                    return None, None, None, None
            except Exception as e:
                logger.error(f"Error al ejecutar FFmpeg: {str(e)}")
                return None, None, None, None
            
            logger.info(f"Audio procesado correctamente: {processed_audio_path}")

            # Procesar el audio utilizando FileHandler
            try:
                response_text, tts_audio_path, s3_audio_path, transcribed_text_body, task_type = self.file_handler.handle_audio(processed_audio_path, user_id, module_manager, thread)
            except Exception as e:
                logger.error(f"Error en la transcripción de audio: {str(e)}")
                return None, None, None, None

            print(f"Transcripción: {transcribed_text_body}")
            print(f"Respuesta TTS audio path: {tts_audio_path}")
            print(f"S3 audio path: {s3_audio_path}")

            public_s3_audio_path = self.get_presigned_url(s3_audio_path)
            return transcribed_text_body, task_type, response_text, public_s3_audio_path
            
        except Exception as e:
            logger.error(f"Error manejando el archivo de audio: {str(e)}")
            print(f"Error en handle_audio_message: {str(e)}")
            return None

        finally:
            # Eliminar archivos temporales si existen
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Archivo temporal eliminado: {audio_path}")
            
            if processed_audio_path and os.path.exists(processed_audio_path):
                os.remove(processed_audio_path)
                logger.info(f"Archivo temporal procesado eliminado: {processed_audio_path}")

    def handle_image_message(self, file, user_id, thread, module_manager):
        """
        Maneja la subida de imágenes, las guarda localmente, las sube a S3 y clasifica la consulta.
        
        Args:
            file (InMemoryUploadedFile): El archivo de imagen recibido.
            user_id (str): El ID del usuario que sube la imagen.
            thread: Hilo de conversación.
            module_manager: Manejador de módulos.
        
        Returns:
            JsonResponse: Respuesta con los detalles del proceso o un mensaje de error.
        """
        try:
            # Llamar a la función handle_image para manejar el archivo de imagen
            task_type, response_text, s3_image_path = self.file_handler.handle_image(file, user_id, module_manager, thread,is_whatsapp=False)

            if not s3_image_path:
                raise ValueError("Error al guardar la imagen en S3 o al procesarla.")

            
            return task_type, response_text, s3_image_path

        except Exception as e:
            logger.error(f"Error en la subida de la imagen: {str(e)}")
            return JsonResponse({'error': f"Error en la subida de la imagen: {str(e)}"}, status=500)


    def handle_db_message(self, file, user_id, module_manager, thread):
        """
        Maneja la subida de archivos .db, los guarda localmente y los procesa utilizando un manejador.
        
        Args:
            file (InMemoryUploadedFile): El archivo .db recibido.
            user_id (str): El ID del usuario que sube el archivo.
            module_manager: Manejador de módulos.
            thread: Hilo de conversación.
        
        Returns:
            tuple: Respuesta con los detalles del proceso o un mensaje de error.
        """
        try:
            print("Iniciando manejo del archivo .db...")
            print(f"Detalles del archivo recibido: Nombre: {file.name}, Tamaño: {file.size}, Tipo: {file.content_type}")
            print(f"Usuario ID: {user_id}, Thread: {thread}")
            # Llamar a la función handle_db para manejar el archivo .db
            task_type, response_text, s3_db_path = self.file_handler.handle_db_message(file, user_id, module_manager, thread)
            print(f"Resultado de handle_db_message: task_type={task_type}, response_text={response_text}, s3_db_path={s3_db_path}")
            # Si no se pudo procesar el archivo correctamente, lanzar un error
            if not s3_db_path:
                raise ValueError("Error al procesar el archivo .db.")
            print("Archivo procesado con éxito. Retornando resultados...")
            # Retornar el tipo de tarea, el texto de respuesta y la ruta del archivo
            return task_type, response_text, s3_db_path

        except Exception as e:
            logger.error(f"Error en la subida del archivo .db: {str(e)}")
            return JsonResponse({'error': f"Error en la subida del archivo .db: {str(e)}"}, status=500)

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
            # Extraer solo la clave del archivo en S3
            if "https://" in s3_key:  # Si el s3_key ya es una URL completa, lo cortamos
                s3_key = s3_key.split(".com/")[-1]

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
