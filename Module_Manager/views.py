from openai import OpenAI
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
from File_Manager.services import FileManager 
from .services import ModuleManager

class ClassifyQueryView(View):
    def get(self, request):
        manager = ModuleManager()
        query = request.GET.get('query', '')
        print(query)
        if query:
            try:
                response = manager.classify_query(query)
                manager.process_tasks()
                if isinstance(response, dict):
                    return JsonResponse(response)
                else:
                    return JsonResponse({'response': response})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=501)
        return JsonResponse({'error': 'No query provided'}, status=400)


class ChatView(View):
    def get(self, request):
        return render(request, 'chat.html')