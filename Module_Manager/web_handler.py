from .file_handler import FileHandler
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class WebHandler:

    def __init__(self):
        self.file_handler = FileHandler()

    def handle_file_upload(self, request, module_manager, thread):
        """
        Maneja la subida de archivos (imágenes y archivos .db) desde la web.
        """
        try:
            user_id = request.POST.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'No user ID provided for file upload'}, status=400)

            file = request.FILES['file']
            file_type = file.content_type

            # Procesar imágenes
            if file_type.startswith('image/'):
                # Utilizar self.file_handler para manejar las imágenes
                file_path = self.file_handler.handle_image(file, user_id, thread.thread_id)
                response = f"Imagen recibida y almacenada en {file_path}."

            # Procesar archivos .db
            elif file.name.endswith('.db'):
                # Utilizar self.file_handler para manejar archivos .db
                file_path = self.file_handler.handle_db(file, user_id)
                response = f"Archivo .db recibido y almacenado en {file_path}."

            else:
                return JsonResponse({'error': 'Unsupported file type'}, status=400)

            return JsonResponse({'response': response})

        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return JsonResponse({'error': f"Error en la subida del archivo: {str(e)}"}, status=500)

    def handle_text_message(self, message, user_id, module_manager, thread):
        """
        Maneja un mensaje de texto enviado desde la web.
        """
        response, task_type = self.file_handler.handle_text(thread, message, user_id, module_manager)
        return response, task_type
