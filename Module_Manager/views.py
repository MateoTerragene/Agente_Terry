import openai
import json
import os
from django.http import JsonResponse
from django.views import View
from dotenv import load_dotenv
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .thread_manager import ThreadManager

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ModuleManager(View):
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.docs = "COA = certificado de calidad = certificado de analisis, IFU = Prospecto , PD = Descripcion de producto = Ficha tecnica, SDS = Hoja de seguridad, CC = Color chart, FDA = Certificado FDA = 510K "
        self.prompt = f"""Eres un asistente que clasifica consultas de usuarios e identifica tareas a realizar. Puede haber multiples tareas en una consulta. \
                Tu respuesta debe ser un JSON que indique si has recibido una 'fileRequest' (solicitud de documentos), una 'technical_query' (consulta técnica), \
                un 'complaint' (reclamo) o un 'purchase_oportunity' (consulta de compra).  Los documentos que te puede pedir el usuario son: {self.docs}.\
                Debes responder únicamente en el siguiente formato JSON: \
                {{
                    "tasks": [
                        "technical_query" | "fileRequest" | "complaint" | "purchase_opportunity"
                    ]
                }}"""
        self.tasks = []

    def classify_query(self, query):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.prompt}, 
                {"role": "user", "content": f"Clasifica la siguiente consulta y genera el JSON correspondiente: {query}"}
            ],
            max_tokens=150
        )
        classification = response.choices[0].message.content.strip()
        classification_json = json.loads(classification)
        self.tasks.extend(classification_json["tasks"])
        return classification_json

    def process_tasks(self):
        while self.tasks:
            task = self.tasks.pop(0)
            self.resolve_task(task)

    def resolve_task(self, task):
        if task == "fileRequest":
            print("Resolviendo solicitud de documentos...")
            # Lógica para resolver solicitud de documentos
        elif task == "technical_query":
            print("Resolviendo consulta técnica...")
            # Lógica para resolver consulta técnica
        elif task == "complaint":
            print("Resolviendo reclamo...")
            # Lógica para resolver reclamo
        elif task == "purchase_opportunity":
            print("Resolviendo oportunidad de compra...")
            # Lógica para resolver oportunidad de compra
        else:
            print(f"Tarea desconocida: {task}")

class ClassifyQueryView(View):
    def get(self, request):
        manager = ModuleManager()
        query = request.GET.get('query', '')
        if query:
            response = manager.classify_query(query)
            manager.process_tasks()
            return JsonResponse(response)
        return JsonResponse({'error': 'No query provided'}, status=400)


class QueryView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        query = request.data.get('query')
        
        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)

        thread_manager = ThreadManager()
        thread = thread_manager.get_or_create_active_thread(user)
        
        # Aquí iría la lógica para manejar la query con OpenAI y obtener la respuesta
        response = self.handle_query(thread, query)
        
        return Response({'response': response}, status=status.HTTP_200_OK)
class ChatView(View):
    def get(self, request):
        return render(request, 'chat.html')