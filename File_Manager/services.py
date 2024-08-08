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


class FileManager:
    def __init__(self):
        try:
            self.prompt_extract_parameters = None
            self.products = None
            self.document_types = None
            self.prompt_gather_parameters = None
            self.historial = []
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.document_types_string = ""
            self.products_string = ""
            self.prompt = None  # Initialize prompt as None initially
            
            # Check if data is loaded correctly
            response = self.load_data()
            if isinstance(response, JsonResponse):
                print(response.content.decode())
                return  # Exit __init__ if loading data failed

            # Set the prompt after loading data
            self.prompt = f"Eres un experto extrayendo información de conversaciones. Extrae las variables importantes (documento, producto y lote) y devuélvelas en formato JSON. Tu rol NO es devolver documentos. Documento solo puede ser igual a {self.document_types_string}. Producto solo puede ser igual a {self.products_string}. NO PIDAS CONFIRMACIÓN."
            self.state = {
                "documento": None,
                "producto": None,
                "lote": None
            }

        except Exception as e:
            print(JsonResponse({'error': f"An error occurred while creating attributes: {str(e)}"}, status=500))

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
        
        # Extrae la respuesta generada por el modelo
        generated_text = response.choices[0].message.content
        print(generated_text)
        return generated_text
    
    def update_state(self, extracted_params): 
        try:
            cleaned_params = extracted_params.strip('```json').strip()
            data = json.loads(cleaned_params)
            
            for key in self.state:
                if key in data and data[key]:
                    self.state[key] = data[key]
        except json.JSONDecodeError as e:
            print(f"La respuesta no es un JSON válido: {e}")
            print(f"Contenido inválido: {cleaned_params}")
            
    def reset_state(self):
        self.state = {
            "documento": None,
            "producto": None,
            "lote": None
        }
        
    def best_match(self, nombre_busqueda, lista_productos):
        
        nombre_normalizado = self.limpiar_texto(nombre_busqueda)
        
        lista_normalizada = [self.limpiar_texto(nombre) for nombre in lista_productos]
        
        mejor_coincidencia = difflib.get_close_matches(nombre_normalizado, lista_normalizada, n=1, cutoff=0.0)
        
        if mejor_coincidencia:
           
            indice = lista_normalizada.index(mejor_coincidencia[0])
           
            return lista_productos[indice]
        else:
            return None
        
    def get_file(self):
        document_type = self.state.get("documento")
        product = self.state.get("producto")
        lote = self.state.get("lote")
        print(f"document_type: {document_type}, product: {product}")

        best_match_product = self.best_match(product, self.products_string)
        if not document_type or not product:
            print("no product or no type")
            return None
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["biologico", "electronica", "lavado", "quimico"]

        for subfolder in subfolders:
            url = f"{base_url}/{document_type}/{subfolder}/{product}/"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf'):
                            if lote:
                                if href.lower().find(lote.lower()) != -1:
                                    return str(url + href)
                            else:
                                return str(url + href)
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return None
    
    def limpiar_texto(self, texto):  #elimina caracteres extraños
        texto=str(texto)
        return re.sub(r'[^a-zA-Z0-9]', '', texto).lower()
        
    def load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path) as f:
                data = json.load(f)
                self.prompt_extract_parameters = data.get("prompt_extract_parameters")
                self.products = data.get("products")
                self.products_string = ", ".join(self.products)
                self.document_types = data.get("document_types")
                self.document_types_string = ", ".join(self.document_types)
                self.prompt_gather_parameters = data.get("prompt_gather_parameters")
            self.historial = [{"role": "system", "content": "Eres un asistente que reune parámetros."}]
            return None
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
    


    def resolve_task(self,task,entry):
        self.load_data()
        ST=FMSubTask('IFU')
        parameters = self.extract_variables(entry)
        self.update_state(parameters)
        file_link = self.get_file()                                             #se obtiene el enlace del doc
        if file_link:                                                                   #si se obtuvo el enlace se concatena en una variable y se cambia el estado de la bandera a 1                   
            additional_context = f" Devuelve el siguiente enlace textual: '{file_link}'" 
            Bandera=1
        else: 
            additional_context = "bt220.png"
       
        ST.set_response(additional_context)
        task.add_subtask(ST)
        task.update_state('completed') 
