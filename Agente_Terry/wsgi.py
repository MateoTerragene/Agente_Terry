from Module_Manager.thread_manager import ThreadManager
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Agente_Terry.settings")
thread_manager_instance = ThreadManager()
application = get_wsgi_application()

