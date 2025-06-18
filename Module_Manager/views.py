import logging
import json
import requests
from django.shortcuts import render, redirect
from django.views import View
from Module_Manager.web_handler import WebHandler
from django.contrib import messages
from passlib.hash import phpass, bcrypt
import hashlib
import base64
from django.db import connections, DatabaseError
from django.utils.decorators import method_decorator
from Module_Manager.thread_manager import thread_manager_instance
from django.views.decorators.csrf import csrf_exempt
from .whatsapp_handler import WhatsAppHandler
from django.http import JsonResponse, HttpResponse
import re
from .models import UserInteraction
from dotenv import load_dotenv
import os
from threading import Thread
import time
import hmac


load_dotenv()
logger = logging.getLogger(__name__)

def convertir_enlaces(texto):
    # Detectar enlaces con formato Markdown y convertirlos a HTML
    markdown_link_regex = re.compile(r'\[([^\]]+)\]\((https?://[^\s]+)\)')
    
    # Reemplazar el formato Markdown con HTML
    texto_converted = markdown_link_regex.sub(r'<a href="\2" target="_blank">\1</a>', texto)
    
    return texto_converted

@method_decorator(csrf_exempt, name='dispatch')
class ClassifyQueryView(View):
    web_handler = WebHandler()
    def post(self, request):
        start_time = time.time()
        try:
            # Obtener el tipo de contenido antes de procesar el cuerpo de la solicitud
            content_type = request.META.get('CONTENT_TYPE')

            # Obtener 'user_id' independientemente del tipo de contenido
            if request.content_type == 'application/json':
                body = json.loads(request.body)
            else:
                body = request.POST

            user_id = body.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'No user ID provided'}, status=400)

            # Verificar la existencia del usuario en la base de datos 'Terragene_Users_Database'
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

            # Manejo de archivo 'multipart/form-data'
            if content_type.startswith('multipart/form-data'):
                print(f"Files received: {request.FILES}")

                file = request.FILES.get('file')  # Obtener el único archivo enviado
                if not file:
                    return JsonResponse({'error': 'No file provided'}, status=400)

                file_type = file.content_type  # Obtener el tipo MIME del archivo
                print(f"File received: {file.name}, size: {file.size} bytes, type: {file_type}")

                if file_type.startswith('audio/'):
                    # Manejo de archivo de audio
                    print(f"Audio received: {file}")
                    transcribed_text_body, task_type, response, response_audio_url = self.web_handler.handle_audio_message(file, user_id, module_manager, thread)

                    # Guardar la interacción en la base de datos
                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"Audio received: {transcribed_text_body}",
                        response=response,
                        task_type=task_type
                    )
                    # print("###########################################")
                    # print(f"response antes de convertir enlaces: {response}")
                    response_text = convertir_enlaces(response)
                    # response_text=response
                    # print(f"response despuess de convertir enlaces: {response_text}")
                    # print("*********************************************")
                    return JsonResponse({'response': response_text, 'audio_response': response_audio_url})

                elif file_type.startswith('image/'):
                    # Manejo de archivo de imagen
                    print(f"Image received: {file}")
                    # Aquí podrías procesar la imagen o guardarla en el servidor
                    task_type, response_text, s3_image_path = self.web_handler.handle_image_message(file, user_id,thread,module_manager)
                    # Guardar la interacción en la base de datos
                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"Image received: {file.name}",
                        response="Image processed",
                        task_type='image_upload'
                    )

                    return JsonResponse({'response': response_text}, status=200)

                elif file_type == 'application/octet-stream':
                    # Manejo de archivo '.db'
                    print(f"DB File received: {file}")
                    response,task_type, db_path=self.web_handler.handle_db_message(file,user_id,module_manager,thread)
                    # Guardar la interacción en la base de datos
                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"DB File received: {db_path}",
                        response=response,
                        task_type=task_type
                    )
                    print(f"response views:{response}")
                    return JsonResponse({'response': response}, status=200)

                else:
                    return JsonResponse({'error': 'Unsupported file type'}, status=400)

            # Manejo de mensajes de texto en formato 'application/json'
            elif content_type.startswith('application/json'):
                query = body.get('query')
                if not query:
                    return JsonResponse({'error': 'No query provided'}, status=400)

                try:
                    # Clasificar la consulta
                    response_text, task_type = self.web_handler.handle_text_message(query, user_id, module_manager, thread)
                    # print("*********************************************")

                    # print(f"response antes de convertir enlaces: {response_text}")
                    response = convertir_enlaces(response_text)
                    # print(f"response despuess de convertir enlaces: {response}")
                    # print("*********************************************")
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

            else:
                print("Unhandled content type.")
                return JsonResponse({'error': 'Unsupported content type'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            total_elapsed = time.time() - start_time
            print(f"Total time for request in ClassifyQueryView: {total_elapsed:.2f} seconds") 

    def get(self, request):
        action = request.GET.get('action')  # Verificar si la acción es crear un nuevo thread

        if action == 'create_thread':
            return self.create_new_thread(request)  # Llamar a la función que creará el thread
        else:
            return JsonResponse({'status': 'error', 'message': 'Acción no válida'}, status=400)


    def create_new_thread(self, request):
        user_id = request.session.get('ID')  # Obtener el ID del usuario de la sesión
        
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'No se encontró el ID del usuario en la sesión'}, status=400)

        try:
            # Limpia las tareas antes de crear un nuevo thread
            
            # Lógica para crear un nuevo thread
            print(f"🧵 Creando un nuevo thread para el usuario con ID: {user_id}")
            thread, module_manager = thread_manager_instance.create_thread(user_id)

            # Guardar el thread_id en la sesión
            request.session['thread_id'] = thread.thread_id

            # Responder con éxito y detalles del thread creado
            return JsonResponse({'status': 'success', 'message': f'Nuevo thread creado con éxito. ID del Thread: {thread.thread_id}'})
        except Exception as e:
            print(f"Error al crear el thread: {e}")
            return JsonResponse({'status': 'error', 'message': f'Error al crear un nuevo thread: {str(e)}'}, status=500)


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

def _check_wp_password(password: str, db_hash: str) -> bool:
    """
    Verify a WordPress‑style password hash against *password*.
    Supports:
        - $wp$  (bcrypt + SHA‑384 + Base64 pre‑hash)
        - $2y$ / $2b$ / $2a$ (plain bcrypt)
        - $P$ / $H$ (portable phpass)
        - 32‑character hexadecimal (legacy MD5, UNSALTED → weak → login allowed but flagged)
    """
    try:
        if db_hash.startswith('$wp$'):
            # Strip the custom prefix and rebuild a regular bcrypt hash
            bcrypt_hash = db_hash.replace('$wp$', '$', 1)
            pre_hash = base64.b64encode(hashlib.sha384(password.encode()).digest()).decode()
            return bcrypt.verify(pre_hash, bcrypt_hash)

        if db_hash.startswith(('$2y$', '$2b$', '$2a$')):
            return bcrypt.verify(password, db_hash)

        if db_hash.startswith(('$P$', '$H$')):
            return phpass.verify(password, db_hash)

        # Very old WordPress exported plain MD5 (32 hex chars, no salt)
        if re.fullmatch(r'[0-9a-fA-F]{32}', db_hash):
            candidate = hashlib.md5(password.encode()).hexdigest()
            return hmac.compare_digest(candidate, db_hash.lower())

    except Exception as exc:          # any Passlib error
        logger.warning("Password-hash verification error: %s", exc)

    return False                       # on any failure, deny login

def process_message(changes):
    whatsapp_handler = WhatsAppHandler()

    value = changes.get('value', {})

    
    message = value['messages'][0]
    message_id = message.get('id')
    message_type = message.get('type')
    phone_number = value['contacts'][0]['wa_id']
    phone_number = phone_number.replace("549", "54")

     # Obtener o crear el thread y module_manager para procesar el mensaje
    thread, module_manager = thread_manager_instance.get_or_create_active_thread(phone_number, is_whatsapp=True)

    # Check the message type and handle accordingly
    if message_type == 'text':
        text_body = message['text']['body']
        print(f"Processing text message: {text_body}")

        # Handle the text message
        response_text, task_type = whatsapp_handler.handle_text_message(text_body, phone_number, module_manager, thread)
        # print(f"response dentro de views: {response_text}")
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
        transcribed_text_body, task_type, response_text, response_audio_url = whatsapp_handler.handle_audio_message(audio_id, phone_number,module_manager, thread)

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
        task_type, response_text, s3_image_path = whatsapp_handler.handle_image_message(image_id, phone_number, module_manager, thread)

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
            query=f'Image: {s3_image_path}',
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
            return render(request, 'login.html')  # Mostrar formulario de inicio de sesión

        # Comprobamos si ya seleccionó un avatar
        avatar_selected = request.session.get('avatar_selected')
        if not avatar_selected:
            # Si no se ha seleccionado un avatar, mostrar la página de selección de avatar
            return render(request, 'avatar.html')

        # Renderizamos el chat con el avatar seleccionado
        user_id = request.session.get('ID')
        return render(request, 'chat.html', {
            'user_id': user_id,
            'avatar_selected': avatar_selected
        })
        

    def post(self, request):
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password', '')

        # Always rotate the session key early to mitigate fixation attacks
        request.session.cycle_key()

        if not username or not password:
            messages.error(request, 'Usuario y contraseña son obligatorios')
            return render(request, 'login.html')

        try:
            with connections['Terragene_Users_Database'].cursor() as cursor:
                cursor.execute(
                    "SELECT ID, user_pass FROM wp_users WHERE user_login = %s",
                    [username]
                )
                row = cursor.fetchone()

            if not row:
                messages.error(request, 'Usuario no encontrado')
                return render(request, 'login.html')

            user_id, password_hash = row
            if _check_wp_password(password, password_hash):
                # Full session reset before login – prevents session fixation
                request.session.flush()
                request.session.cycle_key()

                request.session['user_authenticated'] = True
                request.session['ID'] = user_id
                request.session['avatar_selected'] = False
                logger.info("User %s (ID %s) logged in", username, user_id)
                return redirect('/')

            messages.error(request, 'Contraseña incorrecta')

        except DatabaseError as db_exc:
            logger.error("DB error during login for user '%s': %s", username, db_exc)
            messages.error(request, 'Error al conectar con la base de datos')

        # On any failure fall through to login page
        request.session.cycle_key()
        return render(request, 'login.html')

    def dispatch(self, request, *args, **kwargs):
        # ... (same as before) ...
        if request.path.endswith('set_avatar/'):
            return self.set_avatar(request)
        return super().dispatch(request, *args, **kwargs)

    def set_avatar(self, request):
        # ... (same as before) ...
        if request.method == 'POST':
            data = json.loads(request.body)
            avatar = data.get('avatar')
            if avatar:
                request.session['avatar_selected'] = avatar
                return JsonResponse({'status': 'success', 'message': 'Avatar configurado exitosamente.'})
            return JsonResponse({'status': 'error', 'message': 'No se envió un avatar válido.'}, status=400)
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)


def logout_view(request):
    # Limpiar la sesión y redirigir al login
    user_id = request.session.get('ID', 'Unknown')
    request.session.flush()
    messages.success(request, 'Has cerrado sesión correctamente.')
    logger.info(f"User ID {user_id} logged out.")
    return redirect('/login/')