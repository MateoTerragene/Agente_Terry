import logging
from .models import WhatsAppUser
from Module_Manager.thread_manager import thread_manager_instance

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self, phone_number):
        self.phone_number = phone_number
        self.user, created = WhatsAppUser.objects.get_or_create(phone_number=phone_number)
        self.thread, self.module_manager = self.get_or_create_thread()

    def get_or_create_thread(self):
        try:
            thread, module_manager = thread_manager_instance.get_or_create_active_thread(self.user.id)
            return thread, module_manager
        except Exception as e:
            logger.error(f"Error al obtener o crear thread para el número {self.phone_number}: {str(e)}")
            raise

    def handle_text_message(self, message):
        try:
            response = self.module_manager.classify_query(self.thread, message)
            logger.info(f"Mensaje procesado para {self.phone_number}")
            return response
        except Exception as e:
            logger.error(f"Error procesando mensaje de texto para {self.phone_number}: {str(e)}")
            return str(e)

    # Métodos futuros para manejar imágenes, audios, etc.
    # def handle_image(self, image):
    #     pass

    # def handle_audio(self, audio):
    #     pass