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
            with open(file_path, 'r', encoding='utf-8') as f:
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
                            # print(devolver)
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
                                # print(devolver)
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
    
    def get_cc_file(self, product):
        document_type = 'ColorChart'
        best_match_product = self.best_match(product, self.products)
        
        if not best_match_product:
            print(f"No se encontró una coincidencia para el producto: {product}")
            return None
        
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["biologicos", "Pro1", "lavado", "quimico"]

        for subfolder in subfolders:
            url = f"{base_url}/{document_type}/{subfolder}/"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf') and best_match_product in href:
                            # Devuelve la URL completa del archivo PDF que coincide
                            return f"{url}{href}"
                else:
                    print(f"No se pudo acceder a la URL: {url}")
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return f"No se pudo encontrar el CC de {best_match_product}"
    
    def get_sds_file(self, product):
        document_type = 'Safetydatasheet'
        best_match_product = self.best_match(product, self.products)
        
        if not best_match_product:
            print(f"No se encontró una coincidencia para el producto: {product}")
            return None
        
        # Diccionarios de excepciones: producto -> archivo PDF específico
        excepciones = {
            # Químicos
            "CD": "SDS%20Chemical%20Indicators%20-%20BD,%20CD,%20CS,%20CT,%20IT,%20PCD.pdf",
            "IT": "SDS%20Chemical%20Indicators%20-%20BD,%20CD,%20CS,%20CT,%20IT,%20PCD.pdf",
            "PCD": "SDS%20Chemical%20Indicators%20-%20BD,%20CD,%20CS,%20CT,%20IT,%20PCD.pdf",
            "CT": "SDS%20Chemical%20Indicators%20-%20BD,%20CD,%20CS,%20CT,%20IT,%20PCD.pdf",
            "BD": "SDS%20Chemical%20Indicators%20-%20BD,%20CD,%20CS,%20CT,%20IT,%20PCD.pdf",
            "CDPCD2X": "SDS%20Chemical%20Indicators%20-%20Helix.pdf",
            "KH2X": "SDS%20Chemical%20Indicators%20-%20Helix.pdf",
            "MK": "SDS%20Chemical%20Indicators%20-%20Markers.pdf",
            # Biológicos
            "MC": "SDS%20Biological%20Indicators%20-%20Culture%20media.pdf",
            "BT10S": "SDS%20Biological%20Indicators%20-%20Spore%20Suspensions.pdf",
            "BT20S": "SDS%20Biological%20Indicators%20-%20Spore%20Suspensions.pdf",
            "BT24S": "SDS%20Biological%20Indicators%20-%20Spore%20Suspensions.pdf",
            "BT70S": "SDS%20Biological%20Indicators%20-%20Spore%20Suspensions.pdf",
            "BT": "SDS%20Biological%20Indicators%20-%20SCBI,%20PCD.pdf",
            "PCD": "SDS%20Biological%20Indicators%20-%20SCBI,%20PCD.pdf",
            "KPCD": "SDS%20Biological%20Indicators%20-%20SCBI,%20PCD.pdf",
            "BT40": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BT400": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BT50": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BT60": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BT70": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "KBT400": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BTM": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BTC": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "BTD": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            "WP90": "SDS%20Biological%20Indicators%20-%20Spores%20strips,%20discs,%20sutures,%20coupons.pdf",
            # Electrónica - usando nombres completos
            "IC1020": "SDS%20Accessories.pdf",
            "IC1020FR": "SDS%20Accessories.pdf",
            "IC1020FRLCD": "SDS%20Accessories.pdf",
            "MiniBio": "SDS%20Accessories.pdf",
            "MiniPro": "SDS%20Accessories.pdf",
            "TBIC1020": "SDS%20Accessories.pdf",
            "ICTP": "SDS%20Accessories.pdf",
            "CG3": "SDS%20Accessories.pdf",
            "IRCG3": "SDS%20Accessories.pdf",
            "Wilink": "SDS%20Accessories.pdf",
            # Lavado
            "CCDER": "SDS%20Cleaning%20Indicators%20-%20LUMENIA-LUMENIA%20SIXFLOW.pdf",
            "L": "SDS%20Cleaning%20Indicators%20-%20LUMENIA-LUMENIA%20SIXFLOW.pdf",
        }
        
        # Verifica si el producto coincide con alguna excepción
        for key, filename in excepciones.items():
            if best_match_product == key or best_match_product.startswith(key):
                subfolder = "Quimicos" if key in ["CD", "IT", "PCD", "CT", "BD", "CDPCD2X", "KH2X", "MK"] else \
                            "Biologicos" if key in ["MC", "BT", "PCD", "KPCD", "BT40", "BT400", "BT50", "BT60", "BT70", "KBT400", "BTM", "BTC", "BTD", "WP90"] else \
                            "Electronica" if key in ["Bionova IC10/20 Incubator", "Bionova IC10/20FR", "Bionova IC10/20FRLCD Auto-Reader Incubators", "Bionova MiniBio Auto-Reader Incubator", "Bionova MiniPro Auto-Reader Incubator", "Bionova TBIC1020 Thermometer for Bionova Incubators", "Bionova ICTP and ICTP Mini Incubator thermal papers", "Chemdye CG3 3-line labeler", "Chemdye IRCG3 Ink roller", "Bionova Wilink Wifi connectivity accessory for Bionova incubators"] else \
                            "Lavado" if key in ["CCDER", "L"] else ""
                return f"https://terragene.com/wp-content/uploads/{document_type}/{subfolder}/{filename}"
        
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["Biologicos", "Electronica", "Lavado", "Quimicos"]

        for subfolder in subfolders:
            url = f"{base_url}/{document_type}/{subfolder}/"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf') and best_match_product in href:
                            # Devuelve la URL completa del archivo PDF que coincide
                            return f"{url}{href}"
                else:
                    print(f"No se pudo acceder a la URL: {url}")
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return f"No se pudo encontrar el SDS de {best_match_product}"


    def get_fda_file(self, product):
        # Diccionarios de excepciones: prefijos y productos específicos -> archivo PDF específico
        fda_files = {
            "K163646": ["BT220", "BT221", "BT222", "BT223", "PCD220-C", "PCD220-2", "PCD222-C", "PCD222-2", "IC10/20FR"],
            "K191021": ["BT95", "BT96", "BT110", "BT224", "PCD224-C", "PCD224-2", "IC10/20FRLCD", "Mini-Bio", 
                        "IT12", "IT26-1YS", "IT26-C", "PCD26-C", "PCD26-2", "CD16", "CD29", "CD40", "CD42", "CT22", "CT40"],
            "K200272": ["BD125X/1", "BD8948X/1", "BDA4/1"],
            "K221641": ["BT98", "BHY", "BNB"]
        }
        
        # Verifica si el producto está en alguna de las listas
        for key, products in fda_files.items():
            if product in products:
                return f"https://terragene.com/wp-content/uploads/Archivos/FDA/{key}.pdf"
        
        return "No se encontró un archivo FDA correspondiente para el producto especificado."

    def get_iso_file(self):
        devolver="""ISO Certification (English): https://terragene.com/wp-content/uploads/Archivos/ISO/243953-2017-AQ-ARG-NA-PS%20Rev%204.0-20230707-20230707084216.pdf
                    Certificado ISO (Español): https://terragene.com/wp-content/uploads/Archivos/ISO/243953-2017-AQ-ARG-NA-PS%20Rev.%204.0%20Spanish-20230707-20230707084303.pdf """
        return devolver