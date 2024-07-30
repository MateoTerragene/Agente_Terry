from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .thread_manager import ThreadManager

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