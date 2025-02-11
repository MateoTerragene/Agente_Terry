from openai import OpenAI
import os
from dotenv import load_dotenv
import time

load_dotenv()

class TechnicalQueryAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')

    def handle_technical_query(self, query, task, thread):
        task.update_state('in_progress')

        try:
            def run_query():
                """
                Ejecuta la consulta en la base de datos (RAG) y devuelve los mensajes de respuesta.
                """
                chat = self.client.beta.threads.messages.create(
                    thread_id=thread.thread_id,
                    role="user",
                    content=f"{query}"
                )

                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=chat.thread_id,
                    assistant_id=self.assistant_id,
                )

                print(f"Run Completed: {run.id}")

                messages_response = self.client.beta.threads.messages.list(
                    thread_id=thread.thread_id,
                    run_id=run.id
                )

                # print("########################################")
                # print(f"messages_response en RAG: {messages_response}")
                # print("########################################")

                return list(messages_response), run.id

            def has_file_citation(messages):
                """
                Verifica si la respuesta contiene citas a la base de datos.
                """
                for message in messages:
                    if hasattr(message, 'content'):
                        for content_block in message.content:
                            if hasattr(content_block, 'text') and hasattr(content_block.text, 'annotations'):
                                for annotation in content_block.text.annotations:
                                    if annotation.type == "file_citation":
                                        print(f"✅ Respuesta contiene citas: {annotation.file_citation.file_id}")
                                        return True  # ✅ Tiene citas
                print("❌ No se encontraron citas en la respuesta.")
                return False

            def was_rag_used(run_id):
                """
                Verifica si el run_id realmente utilizó la base de datos RAG.
                """
                try:
                    run_details = self.client.beta.threads.runs.retrieve(run_id)

                    if hasattr(run_details, "tool_resources") and "file_search" in run_details.tool_resources:
                        print(f"✅ RUN ID {run_id} usó RAG.")
                        return True  # ✅ El asistente usó la base de datos

                except Exception as e:
                    print(f"⚠️ Error al verificar el run_id: {e}")

                print(f"❌ RUN ID {run_id} NO usó RAG.")
                return False

            def eliminar_respuesta(thread_id, message_id):
                """
                Elimina la respuesta inválida del thread para que no contamine el historial.
                """
                try:
                    self.client.beta.threads.messages.delete(
                        thread_id=thread_id,
                        message_id=message_id
                    )
                    print(f"✅ Mensaje {message_id} eliminado del thread {thread_id}.")

                    # Esperar un momento para asegurar que la eliminación se procese
                    time.sleep(2)

                    # Verificar que realmente fue eliminado
                    messages_response = self.client.beta.threads.messages.list(thread_id=thread_id)
                    for message in messages_response:
                        if message.id == message_id:
                            print(f"⚠️ La eliminación de {message_id} falló, sigue en el historial.")
                            return False
                    print(f"✅ Confirmado: {message_id} ya no está en el thread.")
                    return True

                except Exception as e:
                    print(f"⚠️ Error al eliminar el mensaje {message_id}: {e}")
                    return False

            # 🔹 **Ejecutar la consulta**
            messages, run_id = run_query()

            # 🔹 **Verificar si la respuesta tiene citas o si realmente usó RAG**
            if not has_file_citation(messages) and not was_rag_used(run_id):
                print("⚠️ Respuesta sin citas ni confirmación de RAG, intentando de nuevo...")

                # 🔹 **Eliminar respuesta inválida**
                if eliminar_respuesta(thread.thread_id, messages[0].id):
                    messages, run_id = run_query()

                # 🔹 **Si sigue sin referencias, cancelar la respuesta**
                if not has_file_citation(messages) and not was_rag_used(run_id):
                    print("❌ Se bloqueó la respuesta porque no contenía citas ni usó RAG.")
                    eliminar_respuesta(thread.thread_id, messages[0].id)

                    response = "No encontré información en la base de datos para responder esta consulta. Si desea contactar un representante de customer servive hagamelo saber"
                    task.set_response(response)
                    task.update_state('completed')
                    return

            # 🔹 **Si la respuesta es válida, extraer el contenido**
            content_block = messages[0].content[0]
            text_value = content_block.text.value

            # 🔹 **Obtener citas si existen**
            citations = []
            if hasattr(content_block, 'annotations') and content_block.annotations:
                for index, annotation in enumerate(content_block.annotations):
                    if file_citation := getattr(annotation, "file_citation", None):
                        cited_file = self.client.files.retrieve(file_citation.file_id)
                        citations.append(f"[{index}] {cited_file.filename}")

            # 🔹 **Formatear la respuesta final**
            if citations:
                citations_str = "\n".join(citations)
                response = f"{text_value}\n\nCitations:\n{citations_str}"
            else:
                response = text_value  # Si pasó la validación de RAG, se acepta sin citas

            # 🔹 **Configurar la respuesta de la tarea**
            task.set_response(response)
            task.update_state('completed')

        except Exception as e:
            response = f"Error processing technical query: {e}"
            task.set_response(response)
            task.update_state('completed')
