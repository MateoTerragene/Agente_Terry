import os
import hashlib
import boto3
import logging
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
logger = logging.getLogger(__name__)

class FileHandler:

    def handle_text(self, thread, message, phone_number, module_manager, is_whatsapp=False):
        """
        Procesa un mensaje de texto.
        """
        response, task_type = module_manager.classify_query(thread, message, phone_number, is_whatsapp)
        return response, task_type

    def handle_image(self, image_file, phone_number, image_id):
        """
        Maneja una imagen, la guarda localmente y la sube a S3.
        """
        # Guardar localmente la imagen
        image_path = f"uploads/images/{phone_number}/{image_file.name}"
        try:
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            logger.info(f"Imagen guardada exitosamente en {image_path}")
        except Exception as e:
            logger.error(f"Error guardando la imagen localmente: {str(e)}")
            return None

        # Verificar que el archivo existe antes de subirlo a S3
        if not os.path.exists(image_path):
            logger.error(f"El archivo de imagen {image_path} no existe.")
            return None

        # Subir la imagen a S3
        saved_image_path = self.save_image_to_s3(image_path, phone_number, image_id)
        print(f"saved_image_path : {saved_image_path}")
        if not saved_image_path:
            raise ValueError("Error guardando la imagen en S3")
        return saved_image_path

    def handle_audio(self, audio_path, phone_number, module_manager, thread):
        """
        Procesa un mensaje de audio, lo transcribe usando Whisper y genera una respuesta de audio con TTS.
        """
        # Transcribir el audio utilizando Whisper
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        transcribed_text = transcript.text

        if not transcribed_text:
            raise ValueError("Error en la transcripción de audio")

        # Eliminar el archivo después de procesar
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Archivo de audio {audio_path} eliminado exitosamente.")
        else:
            logger.warning(f"El archivo de audio {audio_path} no existe.")

        # Procesar el texto transcrito como un mensaje de texto
        response, task_type = self.handle_text(thread, transcribed_text, phone_number, module_manager)

        # Generar respuesta de audio usando TTS
        tts_audio_path = self.generate_tts_audio(thread, response)
        if not tts_audio_path:
            raise ValueError("Error generando audio de respuesta TTS")
        
        return tts_audio_path
    def handle_db(self, db_file, user_id):
        """
        Procesa y guarda un archivo .db en una ruta específica.
        """
        db_path = f"uploads/databases/{user_id}/{db_file.name}"
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            with open(db_path, 'wb+') as destination:
                for chunk in db_file.chunks():
                    destination.write(chunk)
            logger.info(f"Archivo .db guardado exitosamente en {db_path}")
            return db_path
        except Exception as e:
            logger.error(f"Error guardando archivo .db: {str(e)}")
            return None
    
    def generate_tts_audio(self, thread, text, output_audio_path='/tmp/response_audio.ogg'):
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

            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            if response and response.content:
                with open(output_audio_path, 'wb') as f:
                    f.write(response.content)
                return output_audio_path
            raise ValueError("No se pudo generar el archivo de audio.")
        except Exception as e:
            logger.error(f"Error generando TTS audio: {str(e)}")
            return None

    def save_image_to_s3(self, image_path, phone_number, image_id):
        """
        Sube una imagen a S3 y retorna la URL de la imagen.
        """
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )

            s3_file_name = f"images/{phone_number}_{image_id}.jpg"
            bucket_name = 'agente-terry'

            # Verificar que el archivo exista antes de subirlo
            if os.path.exists(image_path):
                logger.info(f"Subiendo el archivo {image_path} a S3...")
                s3.upload_file(image_path, bucket_name, s3_file_name)
            else:
                logger.error(f"El archivo {image_path} no existe en el sistema de archivos.")
                return None

            file_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
            logger.info(f"Archivo subido exitosamente a S3. URL: {file_url}")
            return file_url

        except Exception as e:
            logger.error(f"Error subiendo la imagen a S3: {str(e)}")
            return None