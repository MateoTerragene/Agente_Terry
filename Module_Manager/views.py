"""
views.py   –   Complete working version

Key fixes
---------
1. wp_pwd_context is configured once and reused everywhere.
2. In the login flow we **do not** call ``hash()`` on the user‑supplied
   password (that would only be done when *creating* or *changing*
   a password).  We only verify.
3. If a WordPress hash is stored with the custom ``$wp$`` prefix,
   we reconstruct it to the underlying bcrypt string before verification.
4. Added extensive logging & defensive error handling, but stripped
   debug ``print()`` calls that would leak inside Docker / gunicorn logs.
"""
import json
import logging
import os
import re
import time
import warnings
from threading import Thread

import requests
from django.contrib import messages
from django.db import DatabaseError, connections
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from passlib.context import CryptContext
from passlib.exc import (
    PasslibSecurityWarning,
    UnknownHashError,
)

from Module_Manager.thread_manager import thread_manager_instance
from Module_Manager.web_handler import WebHandler
from .models import UserInteraction
from .whatsapp_handler import WhatsAppHandler

# --------------------------------------------------------------------------- #
#  Configuration & helpers
# --------------------------------------------------------------------------- #
load_dotenv()
logger = logging.getLogger(__name__)

# WordPress password context
wp_pwd_context = CryptContext(
    schemes=["bcrypt", "phpass"],  # "phpass" handles $P$ / $H$ WordPress hashes
    deprecated="auto",
)

WHATSAPP_API_URL: str | None = os.getenv("WHATSAPP_API_URL")
ACCESS_TOKEN: str | None = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN: str | None = os.getenv("VERIFY_TOKEN")

_MARKDOWN_URL = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def markdown_to_html_links(text: str) -> str:
    """Replace Markdown style links with <a … target="_blank">.</a>."""
    return _MARKDOWN_URL.sub(r'<a href="\2" target="_blank">\1</a>', text)


# --------------------------------------------------------------------------- #
#  ClassifyQueryView
# --------------------------------------------------------------------------- #
@method_decorator(csrf_exempt, name="dispatch")
class ClassifyQueryView(View):
    web_handler = WebHandler()

    # --------------------------- POST -------------------------------------- #
    def post(self, request):
        started = time.time()

        try:
            content_type = request.META.get("CONTENT_TYPE", "")
            body = json.loads(request.body) if request.content_type == "application/json" else request.POST
            user_id = body.get("user_id")
            if not user_id:
                return JsonResponse({"error": "No user ID provided"}, status=400)

            # -- Validate user against wp_users (Terragene_Users_Database) ----
            try:
                with connections["Terragene_Users_Database"].cursor() as cur:
                    cur.execute(
                        """
                        SELECT ID, user_login, user_email, display_name
                          FROM wp_users
                         WHERE ID = %s
                        """,
                        [user_id],
                    )
                    row = cur.fetchone()
                    if not row:
                        return JsonResponse({"error": "User not found"}, status=404)
                    user_id, user_login, user_email, display_name = row
            except Exception as exc:
                logger.exception("Database connection error")
                return JsonResponse({"error": "Database connection error"}, status=500)

            # -- Thread reuse / creation -------------------------------------
            thread, module_manager = thread_manager_instance.get_or_create_active_thread(user_id)

            # ====================== multipart/form-data =====================
            if content_type.startswith("multipart/form-data"):
                uploaded = request.FILES.get("file")
                if not uploaded:
                    return JsonResponse({"error": "No file provided"}, status=400)

                mime = uploaded.content_type or ""
                logger.info("File received: %s (%s bytes – %s)", uploaded.name, uploaded.size, mime)

                if mime.startswith("audio/"):
                    (
                        transcribed_text,
                        task_type,
                        response_text,
                        response_audio_url,
                    ) = self.web_handler.handle_audio_message(uploaded, user_id, module_manager, thread)

                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"Audio received: {transcribed_text}",
                        response=response_text,
                        task_type=task_type,
                    )
                    return JsonResponse(
                        {
                            "response": markdown_to_html_links(response_text),
                            "audio_response": response_audio_url,
                        }
                    )

                if mime.startswith("image/"):
                    task_type, response_text, s3_path = self.web_handler.handle_image_message(
                        uploaded, user_id, thread, module_manager
                    )
                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"Image received: {uploaded.name}",
                        response="Image processed",
                        task_type=task_type or "image_upload",
                    )
                    return JsonResponse({"response": response_text})

                if mime == "application/octet-stream":
                    response_text, task_type, db_path = self.web_handler.handle_db_message(
                        uploaded, user_id, module_manager, thread
                    )
                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=f"DB File received: {db_path}",
                        response=response_text,
                        task_type=task_type,
                    )
                    return JsonResponse({"response": response_text})

                return JsonResponse({"error": "Unsupported file type"}, status=400)

            # ========================= application/json ======================
            if content_type.startswith("application/json"):
                query = body.get("query")
                if not query:
                    return JsonResponse({"error": "No query provided"}, status=400)

                try:
                    response_text, task_type = self.web_handler.handle_text_message(
                        query, user_id, module_manager, thread
                    )
                    html_response = markdown_to_html_links(response_text)

                    UserInteraction.objects.create(
                        thread_id=thread.thread_id,
                        endpoint="ClassifyQueryView",
                        user_id=user_id,
                        user_login=user_login,
                        user_email=user_email,
                        display_name=display_name,
                        query=query,
                        response=html_response,
                        task_type=task_type or "",
                    )
                    return JsonResponse({"response": html_response})

                except Exception as exc:  # noqa: BLE001
                    logger.exception("Error classifying query")
                    return JsonResponse({"error": str(exc)}, status=501)

            return JsonResponse({"error": "Unsupported content type"}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in ClassifyQueryView")
            return JsonResponse({"error": str(exc)}, status=500)
        finally:
            logger.debug("ClassifyQueryView took %.2fs", time.time() - started)

    # ------------------------------ GET ------------------------------------ #
    def get(self, request):
        if request.GET.get("action") == "create_thread":
            return self._create_new_thread(request)
        return JsonResponse({"status": "error", "message": "Acción no válida"}, status=400)

    # ----------------------------------------------------------------------- #
    def _create_new_thread(self, request):
        user_id = request.session.get("ID")
        if not user_id:
            return JsonResponse(
                {"status": "error", "message": "No se encontró el ID del usuario en la sesión"},
                status=400,
            )
        try:
            thread, _ = thread_manager_instance.create_thread(user_id)
            request.session["thread_id"] = thread.thread_id
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Nuevo thread creado con éxito. ID: {thread.thread_id}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error al crear el thread")
            return JsonResponse(
                {"status": "error", "message": f"Error al crear un nuevo thread: {exc}"},
                status=500,
            )


# --------------------------------------------------------------------------- #
#  WhatsAppQueryView
# --------------------------------------------------------------------------- #
@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppQueryView(View):
    whatsapp_handler = WhatsAppHandler()

    # .................... Verification handshake (GET) ..................... #
    def get(self, request):
        if request.GET.get("hub.verify_token") == VERIFY_TOKEN:
            return HttpResponse(request.GET.get("hub.challenge"))
        return HttpResponse("Invalid verification token", status=403)

    # ................................. POST ................................ #
    def post(self, request):
        try:
            body = json.loads(request.body)
            if "entry" not in body:
                return HttpResponse("Unrecognized event", status=400)

            entry = body["entry"][0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})

            # ----------- Delivery status callbacks (sent, delivered …) -------
            if "statuses" in value:
                status_val = value.get("statuses", [])[0].get("status", "unknown")
                logger.debug("WhatsApp delivery status: %s", status_val)
                return HttpResponse("Status update received", status=200)

            # ----------------------------- Messages --------------------------
            if "messages" in value:
                message = value["messages"][0]
                message_id = message["id"]
                if UserInteraction.objects.filter(message_id=message_id).exists():
                    return JsonResponse({"status": "already processed"}, status=200)

                # Acknowledge immediately
                Thread(target=_process_whatsapp_message, args=(changes,)).start()
                _mark_whatsapp_as_read(message_id)
                return HttpResponse("Message received", status=200)

            return HttpResponse("Unrecognized event", status=400)

        except Exception:  # noqa: BLE001
            logger.exception("Error processing WhatsApp webhook")
            return HttpResponse("Server error", status=500)


def _mark_whatsapp_as_read(message_id: str):
    if not (WHATSAPP_API_URL and ACCESS_TOKEN):
        return
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        WHATSAPP_API_URL,
        headers=headers,
        json={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("Failed to mark message as read: %s – %s", resp.status_code, resp.text)


def _process_whatsapp_message(changes: dict):
    """Executed in a background thread."""
    whatsapp_handler = WhatsAppHandler()
    value = changes["value"]
    message = value["messages"][0]
    message_id = message["id"]
    msg_type = message["type"]
    phone = value["contacts"][0]["wa_id"].replace("549", "54")

    thread, module_manager = thread_manager_instance.get_or_create_active_thread(phone, is_whatsapp=True)

    if msg_type == "text":
        query = message["text"]["body"]
        response_text, task_type = whatsapp_handler.handle_text_message(query, phone, module_manager, thread)
        _send_whatsapp_text(phone, response_text)
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone,
            query=query,
            response=response_text,
            task_type=task_type or "",
            message_id=message_id,
        )

    elif msg_type == "audio":
        audio_id = message["audio"]["id"]
        transcript, task_type, response_text, audio_url = whatsapp_handler.handle_audio_message(
            audio_id, phone, module_manager, thread
        )
        _send_whatsapp_text(phone, response_text)
        if audio_url:
            _send_whatsapp_audio(phone, audio_url)
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone,
            query=f"Audio: {transcript}",
            response=response_text,
            task_type=task_type or "",
            message_id=message_id,
        )

    elif msg_type == "image":
        image_id = message["image"]["id"]
        task_type, response_text, s3_path = whatsapp_handler.handle_image_message(
            image_id, phone, module_manager, thread
        )
        _send_whatsapp_text(phone, response_text)
        UserInteraction.objects.create(
            thread_id=thread.thread_id,
            endpoint="WhatsAppQueryView",
            phone_number=phone,
            query=f"Image: {s3_path}",
            response=response_text,
            task_type=task_type or "",
            message_id=message_id,
        )

    else:
        logger.info("Unhandled WhatsApp message type: %s", msg_type)


def _send_whatsapp_text(to: str, body: str):
    if not (WHATSAPP_API_URL and ACCESS_TOKEN):
        return
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    requests.post(WHATSAPP_API_URL, headers=headers, json=data, timeout=10)


def _send_whatsapp_audio(to: str, media_id: str):
    if not (WHATSAPP_API_URL and ACCESS_TOKEN):
        return
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id},
    }
    requests.post(WHATSAPP_API_URL, headers=headers, json=data, timeout=10)


# --------------------------------------------------------------------------- #
#  UserView  – login & avatar selection
# --------------------------------------------------------------------------- #
@method_decorator(csrf_exempt, name="dispatch")
class UserView(View):
    # ------------------------------ GET ------------------------------------ #
    def get(self, request):
        if not request.session.get("user_authenticated", False):
            return render(request, "login.html")

        avatar_selected = request.session.get("avatar_selected")
        if not avatar_selected:
            return render(request, "avatar.html")

        return render(
            request,
            "chat.html",
            {
                "user_id": request.session["ID"],
                "avatar_selected": avatar_selected,
            },
        )

    # ----------------------------- POST (login) ---------------------------- #
    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        # 1️⃣  Fetch hash from WordPress DB
        try:
            with connections["Terragene_Users_Database"].cursor() as cur:
                cur.execute("SELECT ID, user_pass FROM wp_users WHERE user_login=%s", [username])
                row = cur.fetchone()
        except DatabaseError as exc:
            messages.error(request, "Error al conectar con la base de datos")
            logger.exception("DB error during login for %s", username)
            return render(request, "login.html")

        if not row:
            messages.error(request, "Usuario no encontrado")
            logger.warning("Login attempt for unknown user: %s", username)
            return render(request, "login.html")

        user_id, db_hash = row
        logger.info("Login attempt: %s (ID %s)", username, user_id)

        # 2️⃣  Handle custom `$wp$` prefix wrapper around bcrypt
        hash_to_verify = db_hash
        if db_hash.startswith("$wp$"):
            # Strip wrapper → '$2y$10$...'
            candidate = f"${db_hash[4:]}"
            if candidate.startswith(("$2y$", "$2a$", "$2b$")):
                hash_to_verify = candidate
                logger.debug("Reconstructed bcrypt hash for user %s", user_id)

        if not hash_to_verify:
            messages.error(request, "Formato de contraseña no reconocido")
            logger.error("Empty hash in DB for user %s", user_id)
            return render(request, "login.html")

        # 3️⃣  Verify password
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=PasslibSecurityWarning)
                verified = wp_pwd_context.verify(password, hash_to_verify)
        except UnknownHashError:
            verified = False  # Unsupported algorithm
            logger.warning("UnknownHashError for user %s with hash %s", user_id, hash_to_verify)
        except Exception as exc:  # noqa: BLE001
            messages.error(request, "Error al verificar contraseña")
            logger.exception("Error verifying password for %s", username)
            return render(request, "login.html")

        if not verified:
            messages.error(request, "Contraseña incorrecta")
            logger.info("Invalid password for user %s", username)
            return render(request, "login.html")

        # 4️⃣  Successful login – set session & redirect
        request.session["user_authenticated"] = True
        request.session["ID"] = user_id
        request.session["avatar_selected"] = False  # force avatar picker next
        logger.info("User %s authenticated successfully", username)
        return redirect("/")

    # ----------------------------- dispatch -------------------------------- #
    def dispatch(self, request, *args, **kwargs):
        if request.path.endswith("set_avatar/"):
            return self.set_avatar(request)
        return super().dispatch(request, *args, **kwargs)

    # --------------------------- Avatar picker ----------------------------- #
    def set_avatar(self, request):
        if request.method != "POST":
            return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)
        try:
            avatar = json.loads(request.body).get("avatar")
        except json.JSONDecodeError:
            avatar = None
        if avatar:
            request.session["avatar_selected"] = avatar
            return JsonResponse({"status": "success", "message": "Avatar configurado exitosamente."})
        return JsonResponse({"status": "error", "message": "No se envió un avatar válido."}, status=400)


# --------------------------------------------------------------------------- #
#  Logout helper
# --------------------------------------------------------------------------- #
def logout_view(request):
    user_id = request.session.get("ID", "Unknown")
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente.")
    logger.info("User %s logged out", user_id)
    return redirect("/login/")
