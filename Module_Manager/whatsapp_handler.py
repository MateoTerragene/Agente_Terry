from .file_handler import FileHandler
from openai import OpenAI
import os
import requests
import logging

logger = logging.getLogger(__name__)

class WhatsAppHandler:

    def __init__(self):
        self.file_handler = FileHandler()
        self.processed_messages = set()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def handle_audio_message(self, audio_id, phone_number, module_manager, thread):
        """
        Maneja un mensaje de audio de WhatsApp.
        """
        audio_path = self.download_audio(audio_id)
        if not audio_path:
            raise ValueError("No se pudo descargar el audio")

        tts_audio_path = self.file_handler.handle_audio(audio_path, phone_number, module_manager, thread)

        # Subir el archivo de respuesta de TTS a WhatsApp
        media_id = self.upload_audio(tts_audio_path)
        if not media_id:
            raise ValueError("Error subiendo el archivo de audio")

        return media_id

    def handle_image_message(self, image_id, phone_number):
        """
        Maneja una imagen enviada por WhatsApp.
        """
        image_path = self.download_image(image_id, phone_number)
        if not image_path:
            raise ValueError("No se pudo descargar la imagen")

        saved_image_path = self.file_handler.handle_image(image_path, phone_number, image_id)
        return saved_image_path

    def handle_text_message(self, message, phone_number, module_manager, thread):
        """
        Maneja un mensaje de texto de WhatsApp.
        """
        response, task_type = self.file_handler.handle_text(thread, message, phone_number, module_manager, is_whatsapp=True)
        return response, task_type

    # Métodos auxiliares para descargar audio e imágenes desde la API de WhatsApp...
