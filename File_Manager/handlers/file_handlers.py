from bs4 import BeautifulSoup
import requests 
import difflib
from django.http import JsonResponse
import json
import os
import re

class file_handlers:
    
    def __init__(self):
        self.products = []
        self.products_string = "" 

        response = self.load_data()
        if isinstance(response, JsonResponse):
            print(response.content.decode())
            return  
    
    def load_data(self):
        try:
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            file_path = os.path.join(parent_dir, 'data.json')
            with open(file_path) as f:
                data = json.load(f) 
            self.products = data.get("products", [])
            self.products_string = ", ".join(self.products)
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
    
    def best_match(self, nombre_busqueda, lista_productos):
        nombre_normalizado = self.limpiar_texto(nombre_busqueda)
        lista_normalizada = [self.limpiar_texto(nombre) for nombre in lista_productos]
        
        mejor_coincidencia = difflib.get_close_matches(nombre_normalizado, lista_normalizada, n=1, cutoff=0.0)
        
        if mejor_coincidencia:
            indice = lista_normalizada.index(mejor_coincidencia[0])
            return lista_productos[indice]
        else:
            return None
    
    def limpiar_texto(self, texto):  # elimina caracteres extraños
        if texto is None:
            return ''
        return re.sub(r'[^a-zA-Z0-9]', '', str(texto)).lower()   
          
    def get_ifu_file(self, product):
        document_type = 'IFU'
        best_match_product = self.best_match(product, self.products)
        
        if not best_match_product:
            print(f"No se encontró una coincidencia para el producto: {product}")
            return None
        
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["biologico", "electronica", "lavado", "quimico"]

        for subfolder in subfolders:
            url = f"{base_url}/{document_type}/{subfolder}/{best_match_product}/"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf'):
                            return 1, str(url + href) #El 1 significa que se devolvio el link 
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return 1, f"No se pudo encontrar el IFU de {best_match_product}"

    def get_coa_file(self, product, lot):
        if product not in self.products or lot == 'N/A' or lot ==None or lot=="":
            return 1, None  # Mejor usar None para indicarque no se encontró el archivo
        else:
            return 1, f"Este es el COA simulado de {product}, lote: {lot}"
