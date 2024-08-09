from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import Thread
import openai
from Module_Manager.services import ModuleManager
import os
import logging
import time
logger = logging.getLogger(__name__)

class ThreadManager:
    def __init__(self):
        self.client = openai
        self.client.api_key = os.getenv('OPENAI_API_KEY')

    def create_thread(self, user):
        try:
            # Crear un nuevo thread en OpenAI
            openai_thread = self.client.beta.threads.create()
            thread_id = openai_thread.id
            logger.info(f"Thread creado en OpenAI con ID: {thread_id} para el usuario {user.username}")
            print(f"Thread creado en OpenAI con ID: {thread_id} para el usuario {user.username}")
            # Esperar un momento antes de usar el thread
            time.sleep(1)  # Esperar 1 segundo
            
            # Guardar el thread en la base de datos
            thread = Thread.objects.create(user=user, thread_id=thread_id)
            thread.update_last_activity()

            logger.info(f"Thread guardado en la base de datos con ID: {thread.thread_id}")
            
            # Inicializar ModuleManager para el nuevo thread
            module_manager = ModuleManager()
            
            return thread, module_manager
        except Exception as e:
            logger.error(f"Error creando thread para usuario {user.username}: {str(e)}")
            raise

###########################################################3333
    def get_or_create_active_thread(self, user):
        try:
            # Forzar la creación de un nuevo thread para pruebas
            thread, module_manager = self.create_thread(user)
            return thread, module_manager
        except Exception as e:
            logger.error(f"Error al obtener o crear thread para usuario {user.username}: {str(e)}")
            raise


#########################################################33
    # def get_or_create_active_thread(self, user):
    #     try:
    #         # Intentar obtener el thread más reciente para el usuario
    #         thread = Thread.objects.filter(user=user).latest('created_at')
    #         # Verificar si el thread es reciente o necesita uno nuevo
    #         if thread.last_activity < timezone.now() - timedelta(minutes=10):
    #             logger.info(f"Thread antiguo encontrado para el usuario {user.username}. Creando nuevo thread.")
    #             thread, module_manager = self.create_thread(user)
    #         else:
    #             # Reutilizar el thread existente
    #             logger.info(f"Thread reciente encontrado para el usuario {user.username}. Reutilizando thread.")
    #             thread.update_last_activity()
    #             module_manager = ModuleManager()
    #     except Thread.DoesNotExist:
    #         logger.info(f"No se encontró ningún thread para el usuario {user.username}. Creando nuevo thread.")
    #         thread, module_manager = self.create_thread(user)
    #     except Exception as e:
    #         logger.error(f"Error al obtener o crear thread para usuario {user.username}: {str(e)}")
    #         raise

    #     return thread, module_manager

    def delete_thread(self, user):
        try:
            # Desactivar todos los threads activos para el usuario
            Thread.objects.filter(user=user, is_active=True).update(is_active=False)
            logger.info(f"Todos los threads activos desactivados para el usuario {user.username}.")
        except Exception as e:
            logger.error(f"Error al desactivar threads para usuario {user.username}: {str(e)}")
            raise
