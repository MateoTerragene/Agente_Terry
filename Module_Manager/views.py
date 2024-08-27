import logging
import json
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .thread_manager import ThreadManager
from Module_Manager.thread_manager import thread_manager_instance
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db import connections
from .whatsapp_handler import WhatsAppHandler
from .models import UserInteraction
from Module_Manager.models import ExternalUser
import re

logger = logging.getLogger(__name__)

def convertir_enlaces(texto):
    url_regex = re.compile(r'(https?://[^\s]+)')
    return url_regex.sub(r'<a href="\1" target="_blank">\1</a>', texto)

@method_decorator(csrf_exempt, name='dispatch')
class ClassifyQueryView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            user_id = body.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'No user ID provided'}, status=400)

            try:
                with connections['Terragene_Users_Database'].cursor() as cursor:
                    cursor.execute("SELECT ID, user_login, user_email, display_name FROM wp_users WHERE ID = %s", [user_id])
                    result = cursor.fetchone()

                    if not result:
                        return JsonResponse({'error': 'User not found'}, status=404)

                    user_id, user_login, user_email, display_name = result

            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                return JsonResponse({'error': 'Database connection error'}, status=500)

            # Reutilizar thread existente si es posible
            thread, module_manager = thread_manager_instance.get_or_create_active_thread(user_id)

            query = body.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)
            # task_type = None
            try:
                response, task_type = module_manager.classify_query(thread, query,user_id)
                
                response = convertir_enlaces(response)
                
                
                # Guardar la interacción en la base de datos
                UserInteraction.objects.create(
                    thread_id=thread.thread_id,
                    endpoint="ClassifyQueryView",
                    user_id=user_id,
                    user_login=user_login,
                    user_email=user_email,
                    display_name=display_name,
                    query=query,
                    response=response,
                    task_type=task_type if task_type else '' 
                )
                return JsonResponse({'response': response})
            except Exception as e:
                logger.error(f"Error classifying query: {str(e)}")
                return JsonResponse({'error': str(e)}, status=501)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    def get(self, request):
        try:
            # Mostrar la página sin intentar procesar JSON
            return render(request, 'chat.html')
        except Exception as e:
            logger.error(f"Error in ChatView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    def post(self, request):
        try:
            # Solo manejar JSON cuando se recibe una solicitud POST
            body = json.loads(request.body)
            user_id = body.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'No user ID provided'}, status=400)

            query = body.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)

            logger.debug(f"User ID: {user_id}")
            thread, _ = thread_manager_instance.get_or_create_active_thread(user_id)
            response = thread_manager_instance.process_query(thread, query)

            # Guardar la interacción en la base de datos
            UserInteraction.objects.create(
                thread_id=thread.thread_id,
                endpoint="ChatView",
                user_id=user_id,
                query=query,
                response=response
            )

            return JsonResponse({'response': response})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in ChatView POST: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppQueryView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            phone_number = body.get('phone_number')
            if not phone_number:
                return JsonResponse({'error': 'No phone number provided'}, status=400)

            query = body.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)

            # Reutilizar thread existente si es posible, usando el número de teléfono como ID
            thread, module_manager = thread_manager_instance.get_or_create_active_thread(phone_number, is_whatsapp=True)
            # Utilizar classify_query en lugar de process_query
            response, task_type = module_manager.classify_query(thread, query, phone_number, is_whatsapp=True)
            
            # Guardar la interacción en la base de datos
            UserInteraction.objects.create(
                thread_id=thread.thread_id,
                endpoint="WhatsAppQueryView",
                phone_number=phone_number,
                query=query,
                response=response,
                task_type=task_type if task_type else ''
            )

            return JsonResponse({'response': response})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error handling WhatsApp query: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
