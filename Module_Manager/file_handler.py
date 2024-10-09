import os
import hashlib
import boto3
import logging
from openai import OpenAI
from dotenv import load_dotenv
import time
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self):
        # Inicializar cliente OpenAI con la clave de API
        
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def handle_text(self, thread, message, identifier, module_manager, is_whatsapp=False):
        """
        Procesa un mensaje de texto.
        """
        response, task_type = module_manager.classify_query(thread, message, identifier, is_whatsapp)
        print(f"response dentro de file_handler: {response}")
        return response, task_type

    def handle_audio(self, audio_path, identifier, module_manager, thread):
        print("Entrando a handle_audio de file_handler")
        
        # Mantén la ruta completa para el almacenamiento local, pero quita '/tmp/' antes de subir a S3
        file_name = os.path.basename(audio_path)  # Solo el nombre del archivo, sin la ruta '/tmp/'
        
        # Guardar el audio recibido en S3 antes de procesarlo
        received_audio_url = self.save_file_to_s3(audio_path, 'received_audio')
        if not received_audio_url:
            logger.error("Error al guardar el audio recibido en S3.")
            return None, None, None, None, None  # Devuelve None para todos si ocurre un error

        print(f"Audio recibido guardado en S3: {received_audio_url}")

        try:
            # Transcribir el audio utilizando Whisper
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Accediendo al campo 'text' correctamente
            transcribed_text_body = transcript.text
            print(f"Transcripción de Whisper: {transcribed_text_body}")

            if not transcribed_text_body:
                raise ValueError("Error en la transcripción de audio")

        except Exception as e:
            logger.error(f"Error transcribiendo el audio con Whisper: {str(e)}")
            return None, None, None, None, None

        # Eliminar el archivo de audio después de procesar solo si existe
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Archivo de audio {audio_path} eliminado exitosamente.")
        else:
            logger.warning(f"El archivo de audio {audio_path} no existe. No se puede eliminar.")

        # Procesar el texto transcrito como un mensaje de texto
        try:
            response_text, task_type = self.handle_text(thread, transcribed_text_body, identifier, module_manager)
            print(f"Respuesta procesada: {response_text}")
        except Exception as e:
            logger.error(f"Error procesando el texto transcrito: {str(e)}")
            return None, None, None, None, None

        # Generar respuesta de audio usando TTS
        try:
            print(f"Generando audio de respuesta usando TTS para el texto: {response_text}")
            tts_audio_path = self.generate_tts_audio(thread, response_text,identifier)
            print(f"TTS generado en la ruta: {tts_audio_path}")
            
            if not tts_audio_path:
                raise ValueError("Error generando audio de respuesta TTS")

        except Exception as e:
            logger.error(f"Error generando la respuesta de audio TTS: {str(e)}")
            return None, None, None, None, None

        # Guardar el audio de respuesta en S3
        try:
            print(f"Guardando el archivo de respuesta TTS en S3: {tts_audio_path}")
            s3_audio_path = self.save_file_to_s3(tts_audio_path, 'sent_audio')
            
            if not s3_audio_path:
                logger.error("Error al guardar el audio de respuesta en S3.")
                return None, None, None, None, None

            print(f"Audio de respuesta guardado en S3: {s3_audio_path}")

        except Exception as e:
            logger.error(f"Error al subir el audio de respuesta a S3: {str(e)}")
            return None, None, None, None, None

        return response_text, tts_audio_path, s3_audio_path, transcribed_text_body, task_type


    def handle_image(self, image_file, identifier, module_manager, thread, is_whatsapp=False):
        """
        Maneja una imagen, la guarda localmente y la sube a S3.
        """
        # Obtén la extensión del archivo desde el nombre original
        file_extension = os.path.splitext(image_file.name)[1]  # Obtiene la extensión con el punto (e.g., '.jpg')

        # Define la ruta con un identificador único basado en el user_id y el timestamp
        local_image_path = f"uploads/images/{identifier}_{int(time.time())}{file_extension}"
        try:
            # Guardar el archivo localmente
            os.makedirs(os.path.dirname(local_image_path), exist_ok=True)  # Crear directorio si no existe
            with open(local_image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            # Verificar que el archivo existe antes de subirlo a S3
            if not os.path.exists(local_image_path):
                logger.error(f"El archivo de imagen {local_image_path} no existe.")
                return None
            
            # Subir la imagen a S3 utilizando la nueva función
            s3_image_url = self.save_file_to_s3(local_image_path,  'image')
            print(f"s3_image_url: {s3_image_url}")

            if not s3_image_url:
                raise ValueError("Error guardando la imagen en S3")

            # Clasificar la consulta utilizando la URL de S3
            response_text, task_type = module_manager.classify_query(thread, s3_image_url, identifier, is_whatsapp)

            return task_type, response_text, s3_image_url 

        except Exception as e:
            logger.error(f"Error guardando la imagen: {str(e)}")
            return None

    def handle_db(self, db_file, user_id):
        """
        Procesa, guarda un archivo .db en una ruta específica y lo sube a S3.
        
        Args:
            db_file (InMemoryUploadedFile): Archivo .db recibido.
            user_id (str): ID del usuario para generar la ruta.
        
        Returns:
            str: URL del archivo en S3 o None si hubo un error.
        """
        db_path = f"uploads/databases/{user_id}/{db_file.name}"
        try:
            # Crear la carpeta si no existe
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Guardar el archivo localmente
            with open(db_path, 'wb+') as destination:
                for chunk in db_file.chunks():
                    destination.write(chunk)
            logger.info(f"Archivo .db guardado exitosamente en {db_path}")
            
            # Subir el archivo a S3
            file_url = self.save_file_to_s3(db_path,  'db')
            if file_url:
                logger.info(f"Archivo subido exitosamente a S3. URL: {file_url}")
                return file_url
            else:
                logger.error("Error subiendo el archivo a S3.")
                return None
            
        except Exception as e:
            logger.error(f"Error procesando archivo .db: {str(e)}")
            return None

    def generate_tts_audio(self, thread, text, user_id, file_extension='.ogg'):
        """
        Genera una respuesta de audio utilizando TTS (Text to Speech) basada en el thread.
        """
        VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        def get_voice_for_thread(thread_id):
            hash_value = int(hashlib.md5(thread_id.encode()).hexdigest(), 16)
            return VOICES[hash_value % len(VOICES)]

        try:
            thread_id_str = thread.id.hex
            voice = get_voice_for_thread(thread_id_str)
            print(f"Usando la voz: {voice} para el thread: {thread_id_str}")

            # Genera el nombre de archivo de salida
            output_audio_path = f"/tmp/{user_id}_{int(time.time())}{file_extension}"
            print(f"Ruta del archivo TTS generado: {output_audio_path}")

            # Generar el TTS utilizando OpenAI API
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            if response and response.content:
                print(f"Generando archivo de TTS en: {output_audio_path}")
                with open(output_audio_path, 'wb') as f:
                    f.write(response.content)
                return output_audio_path
            else:
                raise ValueError("No se pudo generar el archivo de audio.")
        except Exception as e:
            logger.error(f"Error generando TTS audio: {str(e)}")
            print(f"Error en generate_tts_audio: {str(e)}")
            return None


    def save_file_to_s3(self, file_path,  file_type):
        """
        Sube un archivo a S3 y retorna la URL del archivo.
        
        Args:
            file_path (str): La ruta del archivo local.
            identifier (str): Identificador del usuario o thread.
            file_type (str): Tipo de archivo (por ejemplo, 'image', 'audio_sent', 'audio_received', 'db').
        
        Returns:
            str: URL del archivo en S3 o None si hubo un error.
        """
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )

            # Definir la ruta S3 según el tipo de archivo
            if file_type == 'image':
                s3_path = f"images/{os.path.basename(file_path)}"
            elif file_type in ['sent_audio', 'audio_sent']:
                s3_path = f"voice_messages/sent/{os.path.basename(file_path)}"
            elif file_type in ['received_audio', 'audio_received']:
                s3_path = f"voice_messages/received/{os.path.basename(file_path)}"
            elif file_type == 'db':
                s3_path = f"db/{os.path.basename(file_path)}"
            else:
                logger.error(f"Tipo de archivo no soportado: {file_type}")
                return None

            bucket_name = 'agente-terry'
            
            # Verificar que el archivo exista antes de subirlo
            if os.path.exists(file_path):
                logger.info(f"Subiendo el archivo {file_path} a S3...")
                s3.upload_file(file_path, bucket_name, s3_path)
            else:
                logger.error(f"El archivo {file_path} no existe en el sistema de archivos.")
                return None

            file_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
            logger.info(f"Archivo subido exitosamente a S3. URL: {file_url}")
            return file_url

        except Exception as e:
            logger.error(f"Error subiendo el archivo a S3: {str(e)}")
            return None
