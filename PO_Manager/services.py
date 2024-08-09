# file_manager/services.py
from openai import OpenAI
from .SubTask import FMSubTask
from django.http import JsonResponse
from Module_Manager.Tasks import Task
from File_Manager.SubTask import FMSubTask
import json
import os
import requests 
import difflib
from bs4 import BeautifulSoup
import re


class Purchase_Oportunity:
    def __init__(self):
        try:
            self.person = None
            self.product = None
            self.prompt_gather_parameters = None
            self.historial = []
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.document_types_string = ""
            self.products_string = ""
            self.prompt = None 
            
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return 

            self.prompt = f"Eres un experto extrayendo información de conversaciones. Extrae las variables importantes (documento, producto y lote) y devuélvelas en formato JSON. Tu rol NO es devolver documentos. Documento solo puede ser igual a {self.document_types_string}. Producto solo puede ser igual a {self.products_string}. NO PIDAS CONFIRMACIÓN."
            self.state = {
                "documento": None,
                "producto": None,
                "lote": None
            }

        except Exception as e:
            print(JsonResponse({'error': f"An error occurred while creating attributes: {str(e)}"}, status=500))
