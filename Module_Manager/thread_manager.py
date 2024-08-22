from datetime import timedelta
from django.utils import timezone
from .models import Thread
import openai
from Module_Manager.services import ModuleManager
import os
import logging
from Module_Manager.models import ExternalUser
import time
logger = logging.getLogger(__name__)

class ThreadManager:
    def __init__(self):
        self.client = openai
        self.client.api_key = os.getenv('OPENAI_API_KEY')
        self.module_manager = ModuleManager()

    def get_or_create_active_thread(self, user_id, is_whatsapp=False):
        try:
            if is_whatsapp:
                # Buscar threads activos recientes en SQLite usando phone_number como user_id
                threads = Thread.objects.using('default').filter(user_id=user_id).order_by('-created_at')
                logger.info(f"Threads encontrados: {len(threads)} para el número de teléfono {user_id}")

                for thread in threads:
                    if thread.last_activity >= timezone.now() - timedelta(minutes=10):
                        thread.update_last_activity()
                        return thread, self.module_manager

                # Si no hay threads recientes, crear uno nuevo usando el número de teléfono
                return self.create_thread(user_id, is_whatsapp=True)
            else:
                # Verificar que el usuario existe en la base de datos MySQL usando ExternalUser
                user = ExternalUser.objects.using('Terragene_Users_Database').get(id=user_id)
                logger.info(f"Usuario encontrado: {user.user_login} (ID: {user.id})")

                # Buscar threads activos recientes en SQLite usando user_id
                threads = Thread.objects.using('default').filter(user_id=user.id).order_by('-created_at')
                logger.info(f"Threads encontrados: {len(threads)}")

                for thread in threads:
                    if thread.last_activity >= timezone.now() - timedelta(minutes=10):
                        thread.update_last_activity()
                        return thread, self.module_manager

                # Si no hay threads recientes, crear uno nuevo
                return self.create_thread(user)

        except ExternalUser.DoesNotExist:
            logger.error(f"Usuario con id {user_id} no existe en la base de datos MySQL.")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al obtener o crear thread para usuario {user_id}: {str(e)}")
            raise

    def create_thread(self, user_id, is_whatsapp=False, retries=3, delay=5):
        try:
            for attempt in range(retries):
                try:
                    identifier = user_id if is_whatsapp else user_id.id  # Ajuste para cuando es WhatsApp
                    print(f"Intentando crear un thread en OpenAI para el usuario {identifier}...")
                    openai_thread = self.client.beta.threads.create()
                    thread_id = openai_thread.id
                    print(f"Thread creado en OpenAI con ID: {thread_id}")
                    break
                except Exception as e:
                    print(f"Error al crear thread en OpenAI: {str(e)}")
                    if attempt < retries - 1:
                        print(f"Reintentando en {delay} segundos... ({attempt + 1}/{retries})")
                        time.sleep(delay)
                    else:
                        raise e

            # Crear el thread en la base de datos default (SQLite)
            identifier = user_id if is_whatsapp else user_id.id  # Ajuste para cuando es WhatsApp
            print(f"Creando thread en la base de datos SQLite para el usuario con identificador {identifier}...")
            thread = Thread.objects.using('default').create(user_id=identifier, thread_id=thread_id)
            thread.update_last_activity()
            print(f"Thread guardado en la base de datos SQLite con ID {thread.thread_id}")

            return thread, self.module_manager
        except Exception as e:
            print(f"Error creando thread para usuario {user_id}: {str(e)}")
            raise

thread_manager_instance = ThreadManager()