from .file_handler import FileHandler
from openai import OpenAI
import os
import requests
import logging
import time

logger = logging.getLogger(__name__)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
class WhatsAppHandler:

    def __init__(self):
        self.file_handler = FileHandler()
        self.processed_messages = set()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def handle_text_message(self, message, phone_number, module_manager, thread):
        """
        Maneja un mensaje de texto de WhatsApp.
        """
        response, task_type = self.file_handler.handle_text(thread, message, phone_number, module_manager, is_whatsapp=True)
        print(f"response dentro de whatsapp_handler: {response}")
        return response, task_type

    def handle_audio_message(self, audio_id, phone_number, module_manager, thread):
        """
        Maneja un mensaje de audio de WhatsApp.
        """
        audio_path = self.download_audio(audio_id, phone_number)
        if not audio_path:
            raise ValueError("No se pudo descargar el audio")

        response_text, tts_audio_path, s3_audio_path, transcribed_text_body, task_type = self.file_handler.handle_audio(audio_path, phone_number, module_manager, thread)

        # Subir el archivo de respuesta de TTS a WhatsApp
        response_audio_url = self.upload_audio(tts_audio_path)
        if not response_audio_url:
            raise ValueError("Error subiendo el archivo de audio")

        return transcribed_text_body, task_type, response_text, response_audio_url

    def handle_image_message(self, image_id, phone_number, module_manager, thread):
        """
        Maneja una imagen enviada por WhatsApp.
        """
        image_path = self.download_image(image_id, phone_number)
        if not image_path:
            raise ValueError("No se pudo descargar la imagen")

        task_type, response_text, s3_image_path = self.file_handler.handle_image(image_path, phone_number,module_manager, thread, is_whatsapp=True )
        return task_type, response_text, s3_image_path

    # Métodos auxiliares para descargar audio e imágenes desde la API de WhatsApp...
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
        
    def download_audio(self, media_id,phone_number ):
        try:
            url = f"https://graph.facebook.com/v20.0/{media_id}?access_token={ACCESS_TOKEN}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            #file_extension .ogg funciona bien
            # file_extension = os.path.splitext(file.name)[1]  # Obtiene la extensión con el punto (e.g., '.wav')
            # Define la ruta temporal donde se almacenará el archivo de audio con la extensión correcta
            file_extension='.ogg'
            
            save_path = f"tmp/{phone_number}_{int(time.time())}{file_extension}"
            print(f"Ruta temporal del audio: {save_path}")
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
