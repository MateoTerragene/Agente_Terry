from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import openai
import os
import json
from .models import FormDetails  # Importar el modelo desde models.py

load_dotenv()  # Cargar las variables de entorno desde el archivo .env


class FormManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.assistant_id = os.getenv('COMPLAINT_ASSISTANT_ID')
            self.form = FormDetails()  # Instancia del modelo Django
            print(f"FormManager inicializado correctamente. Tipo de self.form: {type(self.form)}")
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")

    def check_what_is_empty(self, form_details_form):
        ask_for = []
        for field in form_details_form._meta.fields:
            field_name = field.name
            if field_name == 'id':  # Ignorar el campo 'id'
                continue
            value = getattr(form_details_form, field_name)
            if value in [None, "", 0]:
                # Ignorar "additional_comments" si todos los demás campos están llenos
                if field_name == "additional_comments" and len(ask_for) == 0:
                    continue
                ask_for.append(field_name)

        print(f"Campos vacíos detectados: {ask_for}")
        return ask_for


    def add_non_empty_details(self, current_details, new_details):
        print(f"Actualizando detalles con nuevos valores no vacíos: {new_details}")
        for field, value in new_details.items():
            if value not in [None, ""]:
                setattr(current_details, field, value)
        print(f"Detalles actualizados: {current_details}")

    def extract_fields(self, query, ask_for):
        print(f"Extrayendo información con los siguientes campos a buscar: {ask_for}")
        fields_text = ", ".join(ask_for)
        prompt = (
            f"Extract the following information from the user's input: {fields_text}.\n\n"
            f"Please return only the fields that could be extracted in JSON format. "
            f"If you are unable to extract a specific field, include the field in the JSON response with an empty string ('') as its value."
        )
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ]
        )
        extracted_info = response.choices[0].message.content
        print(f"Información extraída: {extracted_info}")
        return extracted_info

    def ask_for_info(self, ask_for, thread):
        print(f"Solicitando información para los siguientes campos: {ask_for}")
        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user",
            content="You are an assistant tasked with collecting information from the user to complete a form. "
            "Your role is to ask for the missing details in a friendly, conversational manner. "
            "You should ask one question at a time, and avoid overwhelming the user with multiple requests at once. "
            "Please be clear and concise, and avoid using lists of questions. If the 'ask_for' list is empty, thank the user and ask how you can assist them further."
            f"\n\nHere is the list of missing fields: {ask_for}."
        )
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.thread_id,
            assistant_id=self.assistant_id,
        )
        if run.status == 'completed':
            messages_response = self.client.beta.threads.messages.list(thread_id=thread.thread_id)
        else:
            print(f"Estado del run: {run.status}")
            return None

        messages = messages_response.data
        latest_message = messages[0]
        ai_chat = None
        if messages and hasattr(latest_message, 'content'):
            content_blocks = messages[0].content
            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                text_block = content_blocks[0]
                if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                    ai_chat = text_block.text.value
        print(f"Respuesta del asistente: {ai_chat}")
        return ai_chat

    def handle_form(self, query, task, thread):
        task.update_state('in_progress')
        try:
            print(f"thread ID: {thread.thread_id}")
            # Asignar el thread ID al campo id del formulario
            self.form.id = thread.thread_id
            print(f"Asignado thread.thread_id al campo id: {self.form.id}")
                
            ask_for = self.check_what_is_empty(self.form)
            extracted_info = self.extract_fields(query, ask_for)
            extracted_info_dict = json.loads(extracted_info)
            print(f"Información procesada del formulario: {extracted_info_dict}")
            self.add_non_empty_details(self.form, extracted_info_dict)
            ask_for = self.check_what_is_empty(self.form)
            ai_response = self.ask_for_info(ask_for, thread)

            if not ask_for or (len(ask_for) == 1 and "additional_comments" in ask_for):
                self.form.save()  # Guardar el formulario completo
                print("[DEBUG] Formulario guardado en la base de datos.")
                ai_response = (
                    "¡Gracias por completar el formulario! Hemos recibido toda la información necesaria. "
                    "Un representante se pondrá en contacto contigo pronto."
                )
                task.update_state('completed')
                task.set_response(ai_response)
                return

            print(f"[DEBUG] Missing fields: {ask_for}")
            ai_response = self.ask_for_info(ask_for, thread)
            task.set_response(ai_response)
        except Exception as e:
            print(f"Error manejando el formulario: {str(e)}")
            raise RuntimeError(f"An error occurred while handling the form: {str(e)}")
        return 0