from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import Thread
import openai
from Module_Manager.services import ModuleManager
import os

class ThreadManager:
    def __init__(self):
        self.client = openai
        self.client.api_key = os.getenv('OPENAI_API_KEY')

    def create_thread(self, user):
        # Crear un nuevo thread en OpenAI y en la base de datos
        openai_thread = self.client.beta.threads.create()
        thread = Thread.objects.create(user=user, thread_id=openai_thread.id)
        thread.update_last_activity()
        
        # Inicializar ModuleManager para el nuevo thread
        module_manager = ModuleManager()
        
        return thread, module_manager

    def get_or_create_active_thread(self, user):
        try:
            # Intentar obtener el thread más reciente para el usuario
            thread = Thread.objects.filter(user=user).latest('created_at')
            
            # Verificar si el thread es reciente o necesita uno nuevo
            if thread.last_activity < timezone.now() - timedelta(minutes=10):
                thread, module_manager = self.create_thread(user)
            else:
                # Si el thread es reciente, inicializar ModuleManager para el thread existente
                module_manager = ModuleManager()
        except Thread.DoesNotExist:
            # Si no existe un thread, crear uno nuevo junto con un nuevo ModuleManager
            thread, module_manager = self.create_thread(user)
        
        return thread, module_manager

    def delete_thread(self, user):
        # Desactivar todos los threads activos para el usuario
        Thread.objects.filter(user=user, is_active=True).update(is_active=False)
