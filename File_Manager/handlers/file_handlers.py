from bs4 import BeautifulSoup
import requests 
import difflib
from django.http import JsonResponse
import json
import os
import re
from urllib.parse import urljoin
from datetime import datetime

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

    def get_most_recent_pdf(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a')
                
                most_recent_url = None
                most_recent_date = None

                for link in links:
                    href = link.get('href')
                    if href and href.endswith('.pdf'):
                        pdf_url = urljoin(url, href)
                        head_response = requests.head(pdf_url)
                        if 'Last-Modified' in head_response.headers:
                            last_modified = head_response.headers['Last-Modified']
                            last_modified_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
                            
                            if most_recent_date is None or last_modified_date > most_recent_date:
                                most_recent_date = last_modified_date
                                most_recent_url = pdf_url

                return most_recent_url
            else:
                return "No se pudo acceder a la página."
        except requests.RequestException as e:
            return f"Error al acceder a {url}: {e}"



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
                            devolver=self.get_most_recent_pdf(url)
                            return  devolver #El 1 significa que se devolvio el link 
                            # return  str(url + href) #El 1 significa que se devolvio el link 
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return  f"No se pudo encontrar el IFU de {best_match_product}"

    
    def get_coa_file(self, product, lot):
        document_type = 'COA'
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
                    
                    if lot == "last":
                        most_recent_pdf = self.get_most_recent_pdf(url)
                        if most_recent_pdf:
                            devolver = f"{document_type} - {best_match_product} : {most_recent_pdf}"
                            print(devolver)
                            return devolver
                        else:
                            print(f"No se encontró un PDF reciente para el producto: {product}")
                            return None
                    
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf'):
                            nombre_archivo_limpio = self.limpiar_texto(href)
                            lote_limpio = self.limpiar_texto(lot) if lot else ""
                            if not lot or lote_limpio in nombre_archivo_limpio:
                                devolver = f"{document_type} - {best_match_product} : {url}{href}"
                                print(devolver)
                                return devolver
                else:
                    print(f"No se pudo acceder a la página: {url}")
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        raise FileNotFoundError(f"No PDF found for producto '{product}' y lote '{lot}'.")


    def get_dp_file(self, product):
        document_type = 'PD'
        best_match_product = self.best_match(product, self.products)
        
        if not best_match_product:
            print(f"No se encontró una coincidencia para el producto: {product}")
            return None
        
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["biologicos", "electronica", "lavado", "quimicos"]

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
                            # devolver= f"{document_type} - {best_match_product} :{url}+{href} "
                            devolver=self.get_most_recent_pdf(url)
                            return  devolver #El 1 significa que se devolvio el link 
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return  f"No se pudo encontrar la DP de {best_match_product}"