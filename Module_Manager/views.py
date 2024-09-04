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
from Module_Manager.models import ExternalUser
from django.http import JsonResponse, HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
import re
import requests
from datetime import datetime, timezone
from .models import UserInteraction
from dotenv import load_dotenv
import os
load_dotenv()
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
        
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppQueryView(View):
    
    def get(self, request):
        
        token_sent = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if token_sent == VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse('Invalid verification token', status=403)
    
    def post(self, request):
        try:
            body = json.loads(request.body)
            # print(f"Received JSON body: {json.dumps(body, indent=2)}")  # Imprime el JSON completo recibido

            # Verificar que 'entry' y 'changes' existen y tienen contenido
            if not body.get('entry'):
                print("No 'entry' found in JSON body.")
                return HttpResponse('No entry found', status=400)
            
            entry = body['entry'][0]

            if not entry.get('changes'):
                print("No 'changes' found in entry.")
                return HttpResponse('No changes found', status=400)
            
            changes = entry['changes'][0]

            value = changes.get('value', {})

            if 'contacts' in value and 'messages' in value:
                # Procesar mensajes entrantes
                contacts = value.get('contacts', [])
                messages = value.get('messages', [])
                
                if not contacts:
                    print("No 'contacts' found in value.")
                    return HttpResponse('No contacts found', status=400)
                
                if not messages:
                    print("No 'messages' found in value.")
                    return HttpResponse('No messages found', status=400)
                
                phone_number = contacts[0].get('wa_id')
                phone_number = phone_number.replace("549", "54")  # Modificación temporal para probar
                query = messages[0].get('text', {}).get('body')
                timestamp = int(messages[0].get('timestamp', 0))  # Obtener el timestamp del mensaje

                if not phone_number or not query:
                    print("Phone number or query missing in the message.")
                    return HttpResponse('Phone number or query missing', status=400)

                # Convertir timestamp a datetime
                message_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

                # Verificar si el mensaje fue enviado hace más de 24 horas
                time_difference = (datetime.now(timezone.utc) - message_time).total_seconds()
                if time_difference > 86400:
                    print("Message is older than 24 hours, cannot respond.")
                    return HttpResponse('Message older than 24 hours', status=400)

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

                # Enviar respuesta a WhatsApp
                headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }

                data = {
                    "messaging_product": "whatsapp",
                    "to": phone_number,
                    "text": {
                        "body": response
                    }
                }

                api_response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
                print(f"WhatsApp API Response: {api_response.status_code}, {api_response.text}")
                
                # Manejar la respuesta de la API de WhatsApp
                if api_response.status_code == 200:
                    print("Message sent successfully.")
                    return JsonResponse({'status': 'Message sent successfully'})
                else:
                    print(f"Error sending message: {api_response.text}")
                    return JsonResponse({'error': 'Failed to send message'}, status=500)

            elif 'statuses' in value:
                # Procesar eventos de estado de mensaje
                statuses = value.get('statuses', [])
                if not statuses:
                    print("No 'statuses' found in value.")
                    return HttpResponse('No statuses found', status=400)

                status_info = statuses[0]
                message_status = status_info.get('status')
                recipient_id = status_info.get('recipient_id')
                print(f"Message status update received: {message_status} for recipient {recipient_id}")

                # No realizar ninguna acción específica aquí, ya que solo se está procesando un evento de estado

                return HttpResponse('Status received', status=200)

            else:
                print("No recognized keys in 'value'.")
                return HttpResponse('Unrecognized event', status=400)

        except Exception as e:
            print(f"Error handling WhatsApp query: {str(e)}")
            return HttpResponse(status=500)
