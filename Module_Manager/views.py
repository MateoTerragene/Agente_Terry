import logging
import json
import requests
from django.shortcuts import render, redirect
from django.views import View

import hashlib
import bcrypt
from passlib.hash import phpass
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connections, DatabaseError
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .thread_manager import ThreadManager
from Module_Manager.thread_manager import thread_manager_instance
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .whatsapp_handler import WhatsAppHandler
from Module_Manager.models import ExternalUser
from django.http import JsonResponse, HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
import re
from datetime import datetime, timezone
from .models import UserInteraction
from dotenv import load_dotenv
import os
from threading import Thread
from django.db import connections, DatabaseError

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


        
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppQueryView(View):
    whatsapp_handler = WhatsAppHandler()

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
            # print(f"body: {body}")
            if 'entry' in body:
                entry = body['entry'][0]
                changes = entry.get('changes', [])[0]
                value = changes.get('value', {})
                 #Verifica si es un estado de entrega y no un mensaje de texto/audio
                if 'statuses' in value: 
                    status = value.get('statuses', [])[0]  # Obtenemos el primer estado en la lista
                    status_type = status.get('status')  # Extraemos el valor de 'status'
                    print(f"Status received: {status_type}")  # Solo imprimimos 'sent', 'delivered', etc.
                    return HttpResponse('Status update received', status=200)
                if 'messages' in value:
                    message = value['messages'][0]
                    message_id = message.get('id')

                    # Check if the message has already been processed
                    if UserInteraction.objects.filter(message_id=message_id).exists():
                        return JsonResponse({'status': 'already processed'}, status=200)

                    # Immediately send HTTP 200 response
                    JsonResponse({'status': 'received'}, status=200)
                    headers = {
                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                    mark_read_data = {
                            "messaging_product": "whatsapp",
                            "status": "read",
                            "message_id": message['id']
                        }
                    mark_read_response = requests.post(WHATSAPP_API_URL, headers=headers, json=mark_read_data)

                    if mark_read_response.status_code == 200:
                        print("Message marked as read successfully!")
                    else:
                        print(f"Failed to mark as read: {mark_read_response.status_code}, {mark_read_response.text}")
                    # Start a new thread to process the message in the background
                    processing_thread = Thread(target=process_message, args=(changes,))
                    processing_thread.start()
                    # print("*************HTTP 200************")
                    return HttpResponse('Message received and being processed', status=200)

            return HttpResponse('Unrecognized event', status=400)

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {str(e)}")
            return HttpResponse('Error', status=500)

def process_message(changes):
    whatsapp_handler = WhatsAppHandler()

    value = changes.get('value', {})

    
    message = value['messages'][0]
    message_id = message.get('id')
    message_type = message.get('type')
    phone_number = value['contacts'][0]['wa_id']
    phone_number = phone_number.replace("549", "54")

    # Check the message type and handle accordingly
    if message_type == 'text':
        text_body = message['text']['body']
        print(f"Processing text message: {text_body}")

        # Handle the text message
        thread, task_type, response_text = whatsapp_handler.handle_text_message(text_body, phone_number)

        # Optionally, send a response back via WhatsApp (if needed)
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        response_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": response_text
            }
        }
        requests.post(WHATSAPP_API_URL, headers=headers, json=response_data)

        # Save the interaction to the database
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone_number,
            query=text_body,
            response=response_text,
            task_type=task_type if task_type else '',
            message_id=message_id
        )

    elif message_type == 'audio':
        audio_id = message['audio']['id']
        print(f"Processing audio message with ID: {audio_id}")

        # Handle the audio message
        transcribed_text_body, thread, task_type, response_text, response_audio_url = whatsapp_handler.handle_audio_message(audio_id, phone_number)

        # Send the transcribed text back as a message (optional)
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        text_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": response_text
            }
        }
        requests.post(WHATSAPP_API_URL, headers=headers, json=text_data)

        # Optionally send the audio response back as well
        if response_audio_url:
            audio_data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "audio",
                "audio": {
                    "id": response_audio_url
                }
            }
            requests.post(WHATSAPP_API_URL, headers=headers, json=audio_data)

        # Save the interaction to the database
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone_number,
            query=f'Audio message: {transcribed_text_body}',
            response=response_text,
            task_type=task_type if task_type else '',
            message_id=message_id
        )

    elif message_type == 'image':
        image_id = message['image']['id']
        print(f"Processing image message with ID: {image_id}")

        # Handle the image message
        thread, task_type, response_text, saved_image_path = whatsapp_handler.handle_image_message(image_id, phone_number)

        # Optionally send a text response back via WhatsApp
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        response_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": response_text
            }
        }
        requests.post(WHATSAPP_API_URL, headers=headers, json=response_data)

        # Save the interaction to the database
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone_number,
            query=f'Image: {saved_image_path}',
            response=response_text,
            task_type=task_type if task_type else '',
            message_id=message_id
        )

    else:
        print(f"Unhandled message type: {message_type}")

@method_decorator(csrf_exempt, name='dispatch')
class UserView(View):
    def get(self, request):
        # Comprobamos si el usuario está autenticado
        if not request.session.get('user_authenticated', False):
            return render(request, 'login.html')  # No redirigimos, simplemente mostramos el formulario

        # Si está autenticado, renderizamos el chat
        user_id = request.session.get('ID')
        return render(request, 'chat.html', {'user_id': user_id})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            with connections['Terragene_Users_Database'].cursor() as cursor:
                cursor.execute("SELECT ID, user_pass FROM wp_users WHERE user_login=%s", [username])
                row = cursor.fetchone()

                if row:
                    user_id, contraseña_hash = row
                    if phpass.verify(password, contraseña_hash):
                        # Si la autenticación es exitosa, guardamos la sesión
                        request.session['user_authenticated'] = True
                        request.session['ID'] = user_id
                        return redirect('/')  # Redirigir a la página principal
                    else:
                        messages.error(request, 'Contraseña incorrecta')
                else:
                    messages.error(request, 'Usuario no encontrado')
        except DatabaseError as e:
            messages.error(request, 'Error al conectar con la base de datos')

        # Si el login falla, volvemos a mostrar el formulario de login
        return render(request, 'login.html')

def logout_view(request):
    # Limpiar la sesión
    request.session.flush()
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('/login/')