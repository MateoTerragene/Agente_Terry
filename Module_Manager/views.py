import logging
import json
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .thread_manager import ThreadManager
from Module_Manager.thread_manager import thread_manager_instance

logger = logging.getLogger(__name__)

@method_decorator(login_required, name='dispatch')
class ClassifyQueryView(View):

    def post(self, request):
        try:
            # thread_manager = ThreadManager()
            user = request.user
            thread_manager = thread_manager_instance
            # Obtener o crear un thread activo para el usuario
            thread, module_manager = thread_manager.get_or_create_active_thread(user)
            thread.update_last_activity()

            # Procesar el cuerpo de la solicitud como JSON
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)

            query = body.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)

            # Clasificar la consulta utilizando el ModuleManager
            try:
                print("La query es: " + query)
                response = module_manager.classify_query(thread, query)
                logger.info(f"Query classified successfully for user {user.username}")
                return JsonResponse({'response': response})
            except Exception as e:
                logger.error(f"Error classifying query: {str(e)}")
                return JsonResponse({'error': str(e)}, status=501)

        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class ChatView(View):
    def get(self, request):
        return render(request, 'chat.html')
