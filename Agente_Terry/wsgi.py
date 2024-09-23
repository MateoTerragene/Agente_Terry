import os
from django.core.wsgi import get_wsgi_application

# Set the environment variable for Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Agente_Terry.settings")

# Load Django application
application = get_wsgi_application()

# Initialize ThreadManager after the application is fully loaded
from Module_Manager.thread_manager import ThreadManager
thread_manager_instance = ThreadManager()
