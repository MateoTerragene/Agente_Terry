import logging
import json
import requests
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

        
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppQueryView(View):
    processed_messages = set()  # Conjunto para almacenar IDs de mensajes ya procesados
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
            body=None
            # Parse the incoming request
            body = json.loads(request.body)
            
            # Verifica que haya un mensaje entrante
            if 'entry' in body:
                entry = body['entry'][0]
                changes = entry.get('changes', [])[0]
                value = changes.get('value', {})
                

                # Verifica si hay mensajes entrantes
                if 'messages' in value:
                    message = value['messages'][0]
                    message_id = message.get('id')
                    # Verifica si el mensaje ya ha sido procesado
                    if UserInteraction.objects.filter(message_id=message_id).exists():
                        print(f"Message with ID {message_id} has already been processed.")
                        return JsonResponse({'status': 'already processed'}, status=200)
                    
                    message_type = message.get('type')
                    print("##############################################################")
                    print(body)
                    print("##############################################################")
                    headers = {
                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                    
                    # Procesa mensajes de texto
                    if message_type == 'text':
                        text_body = message['text']['body']
                        print(f"es un mensaje de texto: {text_body}")
                        phone_number = value['contacts'][0]['wa_id']
                        phone_number = phone_number.replace("549", "54")

                        # Marcamos el mensaje como leído
                        
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

                        # Responder mensaje de texto
                        thread, task_type, response_text = self.whatsapp_handler.handle_text_message(text_body, phone_number)
                        response_data = {
                            "messaging_product": "whatsapp",
                            "to": phone_number,
                            "type": "text",
                            "text": {
                                "body": response_text
                            }
                        }
                        api_response = requests.post(WHATSAPP_API_URL, headers=headers, json=response_data)

                        if api_response.status_code == 200:
                            print("Message sent successfully!")
                        else:
                            print(f"Failed with status {api_response.status_code}: {api_response.text}")
                        UserInteraction.objects.create(
                            thread_id=thread.thread_id,
                            endpoint="WhatsAppQueryView",
                            phone_number=phone_number,
                            query=text_body if message_type == 'text' else f'Audio message: {text_body}',
                            response=response_text,
                            task_type=task_type if task_type else '',
                            message_id=message_id)
                        return HttpResponse('Message processed', status=200)

                    # Procesa mensajes de audio
                    elif message_type == 'audio':
                        audio_id = message['audio']['id']
                        phone_number = value['contacts'][0]['wa_id']
                        phone_number = phone_number.replace("549", "54")
                        
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
                        #########marcar como escuchado
                        # mark_listened_data = {
                        #     "messaging_product": "whatsapp",
                        #     "status": "listened",
                        #     "message_id": message['id']
                        # }
                        # mark_listened_response = requests.post(WHATSAPP_API_URL, headers=headers, json=mark_listened_data)

                        # if mark_listened_response.status_code == 200:
                        #     print("Message marked as listened successfully!")
                        # else:
                        #     print(f"Failed to mark as listened: {mark_listened_response.status_code}, {mark_listened_response.text}")



                        trabscribed_text_body,thread, task_type, response_text, response_audio_url = self.whatsapp_handler.handle_audio_message(audio_id, phone_number)
                        print(f"es un mensaje de audio: {trabscribed_text_body}")
                        # Enviar respuesta de audio
                        if response_audio_url:
                            audio_data = {
                                "messaging_product": "whatsapp",
                                "to": phone_number,
                                "type": "audio",
                                "audio": {
                                    "id": response_audio_url
                                }
                            }
                            audio_response = requests.post(WHATSAPP_API_URL, headers=headers, json=audio_data)

                            if audio_response.status_code == 200:
                                print("Audio TTS enviado exitosamente.")
                            else:
                                print(f"Error sending audio response: {audio_response.status_code}")
                        # Enviar respuesta de texto
                        if response_text:
                            text_data = {
                                "messaging_product": "whatsapp",
                                "to": phone_number,
                                "type": "text",
                                "text": {
                                    "body": response_text
                                }
                            }
                            text_response = requests.post(WHATSAPP_API_URL, headers=headers, json=text_data)
                            UserInteraction.objects.create(
                                thread_id=thread.thread_id,
                                endpoint="WhatsAppQueryView",
                                phone_number=phone_number,
                                query=text_body if message_type == 'text' else f'Audio message: {trabscribed_text_body}',
                                response=response_text,
                                task_type=task_type if task_type else '',
                                message_id=message_id)
                            if text_response.status_code == 200:
                                print("Texto transcrito enviado exitosamente.")
                            else:
                                print(f"Error sending text response: {text_response.status_code}")

                        
                        return HttpResponse('Message processed', status=200)

                    elif message_type == 'image':
                        image_id = message['image']['id']
                        print(f"Received image with ID: {image_id}")
                        phone_number = value['contacts'][0]['wa_id']
                        phone_number = phone_number.replace("549", "54")

                        # Marcamos el mensaje como leído
                        mark_read_data = {
                            "messaging_product": "whatsapp",
                            "status": "read",
                            "message_id": message_id
                        }
                        mark_read_response = requests.post(WHATSAPP_API_URL, headers=headers, json=mark_read_data)

                        if mark_read_response.status_code == 200:
                            print("Message marked as read successfully!")
                        else:
                            print(f"Failed to mark as read: {mark_read_response.status_code}, {mark_read_response.text}")
                        # Llamar a la función handle_image_message para manejar la imagen
                        thread, task_type,response_text,saved_image_path  = self.whatsapp_handler.handle_image_message(image_id, phone_number)

                        # if saved_image_path:
                        #     print(f"Imagen guardada en: {saved_image_path}")
                        #     # Puedes enviar una respuesta si lo deseas o continuar el procesamiento  
                        #     text_body= saved_image_path
                        #     # Responder a mensajes de imagen
                            
                        response_data = {
                            "messaging_product": "whatsapp",
                            "to": phone_number,
                            "type": "text",
                            "text": {
                                "body": response_text
                            }
                        }
                        api_response = requests.post(WHATSAPP_API_URL, headers=headers, json=response_data)

                        if api_response.status_code == 200:
                            print("Message sent successfully!")
                        else:
                            print(f"Failed with status {api_response.status_code}: {api_response.text}")
                        UserInteraction.objects.create(
                            thread_id=thread.thread_id,
                            endpoint="WhatsAppQueryView",
                            phone_number=phone_number,
                            query=f'Image: {saved_image_path}',
                            response=response_text,
                            task_type=task_type if task_type else '',
                            message_id=message_id)
                        return HttpResponse('Message processed', status=200)
                   
                    else:
                        # print("No message to process or event not relevant.")
                        return HttpResponse('No action needed', status=200)

            return HttpResponse('Unrecognized event', status=400)

        except Exception as e:
            # Print the full error traceback for debugging
            import traceback
            print(f"Unexpected error: {str(e)}")
            traceback.print_exc()

        return HttpResponse('Error', status=500)
    

        