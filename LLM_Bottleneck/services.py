import os
import json
from openai import OpenAI
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class LLM_Bottleneck:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.channel_layer = get_channel_layer()

    def process_responses(self, query, responses):
        if not query or not responses:
            raise ValueError('Both query and responses are required.')
        return self.elaborate_final_response(query, responses)

    def elaborate_final_response(self, query, responses):
        print("Respuestas recibidas para elaborar la respuesta final:", responses)  # Depuración
        if not responses:
            return "No responses en LLM_BOTTLENECK"

        combined_responses = "\n".join(response["content"] for response in responses if "content" in response)
        combined_input = f"Query: {query}\nResponses: {combined_responses}"
        prompt = f"""Eres un asistente que recibe una consulta y múltiples respuestas de diferentes módulos. \
                Tu tarea es elaborar una respuesta final coherente y bien estructurada basada en la consulta y las respuestas proporcionadas. \
                La consulta y las respuestas son las siguientes:\n\n{combined_input}"""

        print("Prompt enviado a OpenAI:", prompt)  # Depuración
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=200,
            temperature=0.5,
            n=1,
            stop=None
        )
        
        final_response = response.choices[0].message.content
        print("Respuesta final generada por OpenAI:", final_response)  # Depuración
        return final_response

    def print_chat(self, message):
        # Implementa esta función para enviar el mensaje al frontend usando WebSockets
        print(f"Mensaje enviado al chatbot: {message}")
        async_to_sync(self.channel_layer.group_send)(
            "chat_group",
            {
                "type": "chat.message",
                "message": message,
            }
        )
