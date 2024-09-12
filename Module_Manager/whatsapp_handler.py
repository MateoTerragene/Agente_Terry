import mimetypes
import logging
import requests
from Module_Manager.thread_manager import thread_manager_instance
from .models import UserInteraction
from datetime import datetime, timezone
import os
from openai import OpenAI
import hashlib
import uuid
from dotenv import load_dotenv
import boto3
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
logger = logging.getLogger(__name__)
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


class WhatsAppHandler:
    def __init__(self):
        
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.processed_messages = set()  # Keep track of processed messages
        self.phone_number = None  # Añadido para almacenar el número de teléfono

    def handle_audio_message(self, audio_id, phone_number):
        print("**************************************************")
        print("LLAMO A HANDLE_AUDIO_MESSAGE")
        print("**************************************************")

        self.phone_number = phone_number 
        try:
            print(f"Handling audio message for audio_id: {audio_id} and phone_number: {phone_number}")
            if audio_id in self.processed_messages:
                logger.info(f"Audio {audio_id} has already been processed.")
                return None, None,None,None,None

            logger.debug(f"Processing audio message for {phone_number}")

            # Descargar el archivo de audio utilizando el audio_id
            audio_path = self.download_audio(audio_id)
            if not audio_path:
                raise ValueError("No se pudo descargar el audio")

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
                print(f"Archivo de audio {audio_path} eliminado exitosamente.")
            else:
                print(f"El archivo de audio {audio_path} no existe.")
            # Procesar el texto transcrito como un mensaje de texto
            thread, task_type, response_text = self.handle_text_message(transcribed_text, phone_number)

            # Generar respuesta de audio usando TTS
            tts_audio_path = self.generate_tts_audio(thread,response_text)
            if not tts_audio_path:
                raise ValueError("Error generando audio de respuesta TTS")

            # Subir el archivo de audio a WhatsApp
            media_id = self.upload_audio(tts_audio_path)
            if not media_id:
                raise ValueError("Error subiendo el archivo de audio")

            # Marcar el audio como procesado
            self.processed_messages.add(audio_id)

            return transcribed_text,thread, task_type, response_text, media_id

        except Exception as e:
            logger.error(f"Error procesando audio para {phone_number}: {str(e)}")
            return None, None, None, None,None

    def download_audio(self, media_id, save_path='/tmp/audio.ogg'):
        try:
            url = f"https://graph.facebook.com/v20.0/{media_id}?access_token={ACCESS_TOKEN}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                media_url = response.json().get("url")
                audio_response = requests.get(media_url, headers=headers, stream=True)
                if audio_response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        for chunk in audio_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return save_path
            logger.error(f"Error descargando el archivo de audio: {response.status_code}")
        except Exception as e:
            logger.error(f"Error en download_audio: {str(e)}")
        return None

    def generate_tts_audio(self, thread, text, output_audio_path='/tmp/response_audio.ogg'):
        # Define las voces disponibles
        VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        
        def get_voice_for_thread(thread_id):
            # Calcula un hash del thread_id y toma un valor entre 0 y len(VOICES) - 1
            hash_value = int(hashlib.md5(thread_id.encode()).hexdigest(), 16)
            return VOICES[hash_value % len(VOICES)]
        
        try:
            # Asegúrate de que `thread.id` sea una cadena
            if not isinstance(thread.id, uuid.UUID):
                raise TypeError("El identificador del hilo debe ser un UUID.")
            
            # Convierte el UUID a una cadena hexadecimal
            thread_id_str = thread.id.hex
            
            # Obtén la voz basada en el thread
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
    def upload_audio(self, file_path):
        try:
            url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media"
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }

            if os.path.exists(file_path):
                print(f"Archivo encontrado en {file_path}.")
                with open(file_path, 'rb') as audio_file:
                    content = audio_file.read()
                    if len(content) > 0:
                        print(f"El archivo tiene {len(content)} bytes.")
                    else:
                        print("El archivo está vacío.")
            else:
                print(f"El archivo {file_path} no existe.")
                return None

            # Cambiamos el tipo de archivo a 'audio/mpeg' para MP3
            files = {
                'file': ('audio.mp3', open(file_path, 'rb'), 'audio/mpeg')
            }
            data = {
                'messaging_product': 'whatsapp',
                'type': 'audio/mpeg'
            }

            print(f"Enviando solicitud POST a {url} con tipo MIME audio/mpeg (MP3)")

            response = requests.post(url, headers=headers, files=files, data=data)

            print(f"POST response status: {response.status_code}, response: {response.text}")

            if response.status_code == 200:
                media_id = response.json().get("id")
                if media_id:
                    print(f"Audio subido exitosamente con media_id: {media_id}")
                    return media_id
                else:
                    print("No se pudo obtener el media_id después de subir el archivo.")
            else:
                print(f"Error subiendo el archivo de audio: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            print(f"Error en upload_audio: {str(e)}")
            return None

    def handle_text_message(self, message, phone_number):
        self.phone_number = phone_number 
        try:
            thread, module_manager = thread_manager_instance.get_or_create_active_thread(phone_number, is_whatsapp=True)
            response, task_type = module_manager.classify_query(thread, message, phone_number, is_whatsapp=True)

            # Defer saving to DB until after sending the response
            return thread, task_type, response
        except Exception as e:
            logger.error(f"Error procesando mensaje de texto para {self.phone_number}: {str(e)}")
            return  str(e)
    def handle_image_message(self, image_id, phone_number):
        print("**************************************************")
        print("LLAMO A HANDLE_IMAGE_MESSAGE")
        print("**************************************************")

        self.phone_number = phone_number
        try:
            print(f"Handling image message for image_id: {image_id} and phone_number: {phone_number}")
            if image_id in self.processed_messages:
                logger.info(f"Image {image_id} has already been processed.")
                return None, None, None

            logger.debug(f"Processing image message for {phone_number}")

            # Descargar el archivo de imagen utilizando el image_id desde la API de WhatsApp
            image_path = self.download_image(image_id, phone_number)
            if not image_path:
                raise ValueError("No se pudo descargar la imagen")

            # Verificar si el archivo existe
            if not os.path.exists(image_path):
                raise ValueError(f"El archivo de imagen {image_path} no existe.")

            # Guardar la imagen en S3
            saved_image_path = self.save_image_to_s3(image_path, phone_number, image_id)
            if not saved_image_path:
                raise ValueError("Error guardando la imagen en S3")

            # Procesar la URL de la imagen en S3 como un mensaje de texto
            thread, task_type, response_text = self.handle_text_message(saved_image_path, phone_number)

            # Marcar la imagen como procesada
            self.processed_messages.add(image_id)

            # Retornar la URL de la imagen guardada en S3, el thread, task_type, response_text y el id de la imagen
            return thread, task_type, response_text, saved_image_path

        except Exception as e:
            logger.error(f"Error procesando imagen para {phone_number}: {str(e)}")
            return None, None, None


    def save_image_to_s3(self, image_path, phone_number, image_id):
        try:
            # Crear un cliente de S3 usando las credenciales del .env
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )

            # Definir el nombre del archivo en S3 basado en phone_number, thread_id e image_id
            s3_file_name = f"images/{phone_number}_{image_id}.jpg"
            
            # Nombre del bucket
            bucket_name = 'agente-terry'

            # Subir el archivo a S3 en la carpeta 'images'
            s3.upload_file(image_path, bucket_name, s3_file_name)

            # Generar una URL pública del archivo en S3 (opcional, si el bucket tiene permisos públicos)
            file_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
            
            print(f"Archivo subido exitosamente a S3. URL: {file_url}")
            return file_url

        except Exception as e:
            print(f"Error subiendo la imagen a S3: {str(e)}")
            return None
        
    def download_image(self, image_id, phone_number, save_path='/tmp'):
        try:
            # URL para obtener el archivo de imagen
            url = f"https://graph.facebook.com/v20.0/{image_id}?access_token={ACCESS_TOKEN}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

            # Solicitud para obtener la URL del archivo de imagen
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                media_url = response.json().get("url")
                
                # Descargar el archivo de imagen desde la URL obtenida
                image_response = requests.get(media_url, headers=headers, stream=True)
                if image_response.status_code == 200:
                    # Crear un nombre de archivo basado en phone_number e image_id
                    image_name = f"{phone_number}_{image_id}.jpg"
                    temp_image_path = os.path.join(save_path, image_name)

                    # Guardar la imagen descargada
                    with open(temp_image_path, 'wb') as f:
                        for chunk in image_response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    print(f"Imagen descargada exitosamente en: {temp_image_path}")
                    return temp_image_path
                else:
                    logger.error(f"Error descargando la imagen. Código de estado: {image_response.status_code}")
            else:
                logger.error(f"Error obteniendo la URL de la imagen: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error en download_image: {str(e)}")
            return None
