from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')
       
    def handle_technical_query(self, query, task, thread):
        task.update_state('in_progress')

        try:
            # Crear el mensaje inicial en el thread
            chat = self.client.beta.threads.messages.create(
                thread_id=thread.thread_id,
                role="user",
                content=f"{query}"
            )

            # Crear y esperar el resultado del run hasta que esté completo
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=chat.thread_id,
                assistant_id=self.assistant_id,
            )

            print(f"Run Completed: {run.id}")

            # Recuperar los mensajes asociados al run
            messages_response = self.client.beta.threads.messages.list(
                thread_id=thread.thread_id,
                run_id=run.id
            )
            messages = list(messages_response)

            if messages and hasattr(messages[0], 'content') and messages[0].content:
                # Obtener el primer bloque de contenido
                content_block = messages[0].content[0]

                if hasattr(content_block, 'text') and hasattr(content_block.text, 'value'):
                    text_value = content_block.text.value

                    # Verificar si hay anotaciones
                    citations = []
                    if hasattr(content_block, 'annotations') and content_block.annotations:
                        for index, annotation in enumerate(content_block.annotations):
                            if file_citation := getattr(annotation, "file_citation", None):
                                cited_file = self.client.files.retrieve(file_citation.file_id)
                                citations.append(f"[{index}] {cited_file.filename}")

                    # Formatear el resultado como un string
                    if citations:
                        citations_str = "\n".join(citations)
                        response = f"{text_value}\n\nCitations:\n{citations_str}"
                    else:
                        response = text_value

                    # Configurar la respuesta de la tarea
                    task.set_response(response)
                    task.update_state('completed')
                    return

            # Si no se encuentran datos válidos
            response = "No valid content found in the response."
            task.set_response(response)
            task.update_state('failed')

        except Exception as e:
            response = f"Error processing technical query: {e}"
            task.set_response(response)
            task.update_state('failed')

