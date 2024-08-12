# file_manager/services.py
from openai import OpenAI
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
            self.amount = None
            self.historial = []
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.products_string = ""
            self.prompt = None 
            
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return 

            self.prompt = f"Eres un experto extrayendo información de conversaciones. Extrae las variables importantes (cantidad y producto) y devuélvelas en formato JSON. Tu rol NO es devolver documentos. Producto solo puede ser igual a {self.products_string}.En caso de que pregunte el precio de algun producto responde que es es informacion esta restringida. NO PIDAS CONFIRMACIÓN."
            self.state = {
                "cantidad": None,
                "producto": None
            }

        except Exception as e:
            print(JsonResponse({'error': f"An error occurred while creating attributes: {str(e)}"}, status=500))

    def load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path) as f:
                data = json.load(f)
                self.prompt_extract_parameters = data.get("prompt_extract_parameters")
                self.products = data.get("products")
                self.products_string = ", ".join(self.products)
                self.prompt_gather_parameters = data.get("prompt_gather_parameters")
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
            return None
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
        
        
    def extract_variables(self, conversation):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": str(conversation)}
            ],
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.5,
        )
        
        generated_text = response.choices[0].message.content
        print(generated_text)
        return generated_text
    
    def reset_state(self):
        self.state = {
                "cantidad": None,
                "producto": None
            }
        
        
    def update_state(self, extracted_params): 
        try:
            print(extracted_params)
            cleaned_params = extracted_params.strip('```json').strip()
            data = json.loads(cleaned_params)
            
            for key in self.state:
                if key in data and data[key]:
                    self.state[key] = data[key]
        except json.JSONDecodeError as e:
            self.state["producto"] = "DIF"
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")
        
    def resolve_task(self, task, entry):
        task.update_state('in_progress')
        self.load_data()

        # Extraer variables
        parameters = self.extract_variables(entry)
        self.update_state(parameters)

        # Verificar si se tienen todos los parámetros
        if self.state['cantidad'] is None or self.state['producto'] is None:
            missing_params = []
            if self.state['cantidad'] is None:
                missing_params.append("cantidad")
            if self.state['producto'] is None:
                missing_params.append("producto")
                
            if self.state['producto'] == "DIF":
                task.set_response(parameters)
                task.update_state('completed')
                return
                
            
            missing_params_str = ", ".join(missing_params)
            task.set_response(f"Faltan los siguientes parámetros: {missing_params_str}. Por favor, proporcione la información.")
            task.update_state('incomplete')
            return
        additional_context = f"Notificamos a nuestro equipo de tu interes de por {self.state['cantidad']} de {self.state['producto']}"


        task.set_response(additional_context)
        task.update_state('completed')
        self.reset_state()
