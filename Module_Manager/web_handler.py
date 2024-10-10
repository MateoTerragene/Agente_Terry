from .file_handler import FileHandler
from django.http import JsonResponse
import logging
import os
import time
import boto3
from django.conf import settings
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
            return response, task_type

        except Exception as e:
            logger.error(f"Text message handling error: {str(e)}")
            return JsonResponse({'error': f"Error en el manejo del mensaje de texto: {str(e)}"}, status=500)

    def handle_audio_message(self, file, user_id, module_manager, thread):
        """
        Maneja la subida de archivos de audio, lo guarda en una ruta temporal y lo procesa.
        
        Args:
            file (InMemoryUploadedFile): El archivo de audio recibido.
            user_id (str): ID del usuario.
            module_manager: Manejador de módulos.
            thread: Hilo de conversación.
        
        Returns:
            dict: Un diccionario con la transcripción del audio, el texto de la respuesta, la ruta del audio TTS, y el tipo de tarea.
        """
        try:
            # Obtén la extensión del archivo desde el nombre original
            file_extension = os.path.splitext(file.name)[1]  # Obtiene la extensión con el punto (e.g., '.wav')
            
            # Define la ruta temporal donde se almacenará el archivo de audio con la extensión correcta
            audio_path = f"/tmp/{user_id}_{int(time.time())}{file_extension}"
            print(f"Ruta temporal del audio: {audio_path}")
            
            # Guarda el archivo de audio en la ruta temporal
            with open(audio_path, 'wb') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            logger.info(f"Archivo de audio guardado temporalmente en {audio_path}")
            print(f"Archivo de audio guardado temporalmente: {audio_path}")
            
            # Procesar el audio utilizando FileHandler
            response_text, tts_audio_path, s3_audio_path, transcribed_text_body, task_type = self.file_handler.handle_audio(audio_path, user_id, module_manager, thread)
            
            # Verifica si se ha procesado correctamente
            print(f"Transcripción: {transcribed_text_body}")
            print(f"Respuesta TTS audio path: {tts_audio_path}")
            print(f"S3 audio path: {s3_audio_path}")
            
            # Verificar si el archivo temporal generado (con la extensión correcta) existe antes de eliminarlo
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Archivo temporal eliminado: {audio_path}")
                print(f"Archivo temporal eliminado: {audio_path}")
            else:
                logger.warning(f"El archivo {audio_path} no existe. No se puede eliminar.")
                print(f"El archivo {audio_path} no existe. No se puede eliminar.")
            public_s3_audio_path= self.get_presigned_url(s3_audio_path)
            # Devolver los detalles del procesamiento
            return transcribed_text_body, task_type, response_text, public_s3_audio_path
            
        except Exception as e:
            logger.error(f"Error manejando el archivo de audio: {str(e)}")
            print(f"Error en handle_audio_message: {str(e)}")
            return None


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


    def handle_db_message(self, file, user_id,module_manager, thread):
        """
        Maneja la subida de archivos .db.
        """
        try:
            # Obtén la extensión del archivo desde el nombre original
            file_extension = os.path.splitext(file.name)[1]  # Obtiene la extensión con el punto (e.g., '.wav')
            
            # Define la ruta temporal donde se almacenará el archivo de archivo db con la extensión correcta
            db_path = f"/tmp/{user_id}_{thread.thread_id}_{int(time.time())}{file_extension}"
            print(f"Ruta temporal del archivo db: {db_path}")
            
            # Guarda el archivo de archivo db en la ruta temporal
            with open(db_path, 'wb') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            logger.info(f"Archivo de archivo db guardado temporalmente en {db_path}")
            print(f"Archivo de archivo db guardado temporalmente: {db_path}")
            response_text,task_type = self.file_handler.handle_db(db_path, user_id,module_manager, thread)
            print(f"response_text_webHandler: {response_text}")
            return response_text, task_type, db_path

        except Exception as e:
            logger.error(f"DB file upload error: {str(e)}")
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
