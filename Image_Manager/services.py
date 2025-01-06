import os
import json
import boto3
import tempfile

from pylibdmtx import pylibdmtx
from openai import OpenAI
from PIL import Image
import requests
import re
# from dbr import BarcodeReader  # Necesita Dynamsoft Barcode Reader SDK

from RAG_Manager.services import TechnicalQueryAssistant
ci_dictionary = {
    "IT261YS": {"GTIN": ["07798164676904"], "product_code": "IT261YS"},
    "IT26C": {"GTIN": ["07798164678151"], "product_code": "IT26C"},
    "CD29": {"GTIN": ["07798164676836"], "product_code": "CD29"},
    "BD125X1": {"GTIN": ["07798164678847"], "product_code": "BD125X1"},
    "BD125X2": {"GTIN": ["07798164677130"], "product_code": "BD125X2"},
    "CD40": {"GTIN": ["07798164676843"], "product_code": "CD40"},
    "CD42": {"GTIN": ["07798164676850"], "product_code": "CD42"},
    "CD16": {"GTIN": ["07798164676805"], "product_code": "CD16"},
    "IT12": {"GTIN": ["07798164676881"], "product_code": "IT12"},
    "CD50": {"GTIN": ["07798164676782"], "product_code": "CD50"},
    "IT26SAD": {"GTIN": ["07798164677246"], "product_code": "IT26SAD"},
    "IT26SBL": {"GTIN": ["07798164679042"], "product_code": "IT26SBL"},
    "PCDBI2RC": {"GTIN": ["07798164675457"], "product_code": "PCDBI2RC"},
    "CDWA3": {"GTIN": ["07798164677215"], "product_code": "CDWA3"},
    "BD8948X1": {"GTIN": ["07798164677871"], "product_code": "BD8948X1"},
    "CDWA4": {"GTIN": ["07798164676799"], "product_code": "CDWA4"},
    "CDWE": {"GTIN": ["07798164676959"], "product_code": "CDWE"},
}

class ImageManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION')
            )
            self.bucket_name = os.getenv('S3_BUCKET_NAME') 
            print(f"ImageManager initialized with bucket: {self.bucket_name}") 
            # self.historial=[]
            self.RAG=TechnicalQueryAssistant()
        except Exception as e:
            print(f"Error al inicializar ImageManager: {e}")

    def get_presigned_url(self, s3_key, expiration=3600):
        """
        Genera una URL firmada para acceder temporalmente a un archivo en S3.
        
        Args:
            s3_key (str): Clave del archivo en S3.
            expiration (int): Tiempo de expiración en segundos (por defecto 1 hora).
        
        Returns:
            str: URL firmada para acceder al archivo.
        """
        try:
            print(f"Generating presigned URL for key: {s3_key} in bucket: {self.bucket_name}")
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            print(f"Presigned URL generated: {response}")
            return response
        except Exception as e:
            print(f"Error al generar la URL firmada: {e}")
            return None
    # Diccionario de productos basado en la estructura de `ciDictionary`


    # def initialize_reader(self):
    #     print("Inicializando el lector de códigos de barras...")
    #     reader = BarcodeReader()
    #     reader.init_license("clavedynam")  # Reemplaza con la clave de Dynamsoft
    #     print("Lector inicializado.")
    #     return reader

    def extract_gtin_from_dtx(self, dtx_code):
        """Extrae el GTIN del código DTX basado en el patrón '01XXXXXXXXXXXXXX'."""
        print(f"Extrayendo GTIN del código DTX: {dtx_code}")
        # Cambia la expresión regular para buscar "01" seguido de 14 dígitos, sin importar el símbolo inicial
        match = re.search(r"01(\d{14})", dtx_code)
        if match:
            gtin = match.group(1)
            print(f"GTIN extraído: {gtin}")
            return gtin
        else:
            print("No se encontró un GTIN válido en el código DTX.")
        return None


    def extract_dtx_codes(self, image_url):
        """Extracts all DTX codes from the image and logs the results without filters."""
        try:
            print(f"Processing the image: {image_url}")
            
            # Descargar la imagen y guardarla en un archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_image:
                response = requests.get(image_url)
                temp_image.write(response.content)
                temp_image.flush()
                temp_image_path = temp_image.name  # Almacena la ruta temporal
                
            # Decodificar el código Data Matrix usando la ruta temporal
            print("Decoding the image for DTX codes...")
            with Image.open(temp_image_path) as image:
                max_size = (1200, 1200)  # Define a maximum size for resizing
                image.thumbnail(max_size, Image.LANCZOS)
                results = pylibdmtx.decode(image)
            
            print(f"Raw results from decode: {results}")  # Verifica el resultado

            if not results:
                print("No codes found in the image.")
                return []

            # Extraer y mostrar los códigos DTX
            dtx_codes = [result.data.decode("utf-8") for result in results]
            for code in dtx_codes:
                print(f"DTX detected: {code}")

            # Extraer y mostrar la lista de GTIN
            gtin_list = [self.extract_gtin_from_dtx(dtx) for dtx in dtx_codes if self.extract_gtin_from_dtx(dtx)]
            print(f"Extracted GTIN list: {gtin_list}")
            
            return gtin_list
        except Exception as e:
            print(f"Error extracting DTX: {e}")
            return []
        finally:
            # Eliminar el archivo temporal después de usarlo
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                    print(f"Temporary file {temp_image_path} removed.")
                except Exception as e:
                    print(f"Error removing temporary file {temp_image_path}: {e}")



    def identify_product_by_gtin(self, gtin_list):
        """Identifica los productos en base a una lista de GTIN."""
        products = []
        for gtin in gtin_list:
            product_found = False
            for product_code, details in ci_dictionary.items():
                if gtin in details["GTIN"]:
                    print(f"GTIN {gtin} asociado al producto: {product_code}")
                    products.append({"gtin": gtin, "product_code": details["product_code"]})
                    product_found = True
                    break
            if not product_found:
                print(f"GTIN {gtin} no encontrado en el diccionario.")
                # products.append({"gtin": gtin, "product_code": "Unknown"})
        return products

    def analyze_image(self, image_url):
        """
        Llama a OpenAI para analizar una imagen y devolver los parámetros obtenidos.
        
        Args:
            image_url (str): URL de la imagen a analizar.
        
        Returns:
            dict: Respuesta generada por OpenAI en formato JSON.
        """
        try:
            print(f"Analyzing image at URL: {image_url}")  # Print para ver la URL de la imagen
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in visual context analysis."
                    },
                    {
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": """
                         Please analyze the following image. If you can identify a product in the image, return the product's Brand, Product Code, and a brief description in a JSON format like this:

                        {
                            "Brand": "Brand Name",
                            "Product Code": "Code",
                            "Lot": "Lot",
                            "Description": "description"
                            
                        }

                        If no product is identified, explain what is seen in the description and return null in brand and product code. Return in Json format.
                        """
                        },
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": f" {image_url}"
                        }
                        }
                    ],
                    }
                ], 
                max_tokens=300,
            )
            
            # Extraer el texto generado
            generated_text = response.choices[0].message.content
            print("Respuesta generada -> analyze_image: ")
            print(generated_text)
            
            # Limpiar el bloque de código Markdown de la respuesta
            clean_response = generated_text.replace("```json", "").replace("```", "").strip()

            # El texto de OpenAI es un JSON, convertir directamente a dict
            result_dict = json.loads(clean_response)
            return result_dict

        except json.JSONDecodeError as json_err:
            print(f"Error al parsear la respuesta a JSON: {json_err}")
            return None
        except Exception as e:
            print(f"Error al analizar la imagen con OpenAI: {e}")
            return None

    def process_image(self, task, s3_url, thread):
        products = None
        query = ""
        task.state = 'in_progress'

        try:
            if not self.bucket_name:
                print("Error: 'bucket_name' no está configurado. Verifica las variables de entorno.")
                task.response = "Error: 'bucket_name' no está configurado."
                task.state = 'completed'
                return

            # Extract S3 key from the URL
            try:
                if s3_url.startswith(f"https://{self.bucket_name}.s3.amazonaws.com/"):
                    s3_key = s3_url[len(f"https://{self.bucket_name}.s3.amazonaws.com/"):]
                else:
                    print("Error: La URL proporcionada no coincide con el bucket.")
                    task.response = "Error: La URL proporcionada no coincide con el bucket."
                    task.state = 'completed'
                    return
            except Exception as e:
                print(f"Error al extraer la clave S3 de la URL: {e}")
                task.response = "Error al procesar la URL de la imagen."
                task.state = 'completed'
                return

            print(f"Processing image with S3 key: {s3_key}")

            # Generate presigned URL
            try:
                presigned_url = self.get_presigned_url(s3_key)
                if presigned_url is None:
                    raise ValueError("Error al generar la URL firmada de la imagen.")
            except Exception as e:
                print(f"Error al generar la URL firmada: {e}")
                task.response = "Error al generar la URL firmada de la imagen."
                task.state = 'completed'
                return

            # Extract DTX codes and GTINs from the image
            try:
                gtin_list = self.extract_dtx_codes(presigned_url)
                products = self.identify_product_by_gtin(gtin_list) if gtin_list else []
            except Exception as e:
                print(f"Error al extraer códigos DTX o identificar productos: {e}")
                task.response = "Error al procesar los códigos en la imagen."
                task.state = 'completed'
                return

            # Formulate query based on products or perform analysis
            if products:
                try:
                    # Format products into a readable string
                    product_descriptions = [f"{prod['product_code']} (GTIN: {prod['gtin']})" for prod in products]
                    query = "En la foto se identifican los siguientes productos: " + ", ".join(product_descriptions)
                    # Final query handling
                    try:
                        self.RAG.handle_technical_query(query, task, thread)
                    except Exception as e:
                        print(f"Error al manejar la consulta técnica: {e}")
                        task.response = "Error al procesar la consulta técnica."
                        task.state = 'completed'
                        return
                except Exception as e:
                    print(f"Error al formatear la lista de productos: {e}")
                    task.response = "Error al formatear la información de productos."
                    task.state = 'completed'
                    return
            else:
                try:
                    # Analyze image if no products found
                    print(f"Using presigned URL for analysis: {presigned_url}")
                    analysis_result = self.analyze_image(presigned_url)
                    product = analysis_result.get("Product Code", "desconocido")
                    lot = analysis_result.get("Lot", "desconocido")
                    description = analysis_result.get("Description", "desconocido")
                    
                    if product is not None:
                        query = f"product: {product}, description: {description}"
                        # Final query handling
                        try:
                            self.RAG.handle_technical_query(query, task, thread)
                        except Exception as e:
                            print(f"Error al manejar la consulta técnica: {e}")
                            task.response = "Error al procesar la consulta técnica."
                            task.state = 'completed'
                            return
                    else:
                        task.response = description
                except Exception as e:
                    print(f"Error al analizar la imagen: {e}")
                    task.response = "Error al analizar la imagen."
                    task.state = 'completed'
                    return

            

            task.state = 'completed'
        except Exception as e:
            print(f"Error general en process_image: {e}")
            task.response = "Error inesperado al procesar la imagen."
            task.state = 'completed'

