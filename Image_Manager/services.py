import os
import json
import boto3
from openai import OpenAI

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
            self.bucket_name = os.getenv('S3_BUCKET_NAME')  # Añadir el nombre del bucket aquí
            print(f"ImageManager initialized with bucket: {self.bucket_name}")  # Print para verificar el bucket
            self.historial=[]
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
            print(f"Generating presigned URL for key: {s3_key} in bucket: {self.bucket_name}")  # Print para ver el s3_key y el bucket
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            print(f"Presigned URL generated: {response}")  # Print para ver la URL generada
            return response
        except Exception as e:
            print(f"Error al generar la URL firmada: {e}")
            return None

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
                    "content": "You are an expert analyzing chemical indicators."
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
                        },*self.historial
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

    def process_image(self, task, s3_url):
        """
        Procesa la tarea de análisis de imagen generando una URL firmada de la imagen en S3, analizándola,
        y almacenando el resultado en `task.response`.
        
        Args:
            task: Tarea a procesar.
            s3_url: URL completa del archivo en S3.
        """
        # Asegúrate de que el bucket_name esté correctamente configurado
        if not self.bucket_name:
            print("Error: 'bucket_name' no está configurado. Verifica las variables de entorno.")
            task.response = "Error: 'bucket_name' no está configurado."
            task.state = 'failed'
            return

        # Extraer la clave S3 desde la URL completa
        if s3_url.startswith(f"https://{self.bucket_name}.s3.amazonaws.com/"):
            s3_key = s3_url[len(f"https://{self.bucket_name}.s3.amazonaws.com/"):]
        else:
            print("Error: La URL proporcionada no coincide con el bucket.")
            task.response = "Error: La URL proporcionada no coincide con el bucket."
            task.state = 'failed'
            return
        
        print(f"Processing image with S3 key: {s3_key}")  # Print para ver el s3_key

        # Generar una URL firmada para la imagen en S3
        presigned_url = self.get_presigned_url(s3_key)

        if presigned_url is None:
            task.response = "Error al generar la URL firmada de la imagen."
            task.state = 'failed'
            print("Error al generar la URL firmada de la imagen.")
            return

        # Analizar la imagen utilizando la URL firmada
        print(f"Using presigned URL for analysis: {presigned_url}")  # Print para ver la URL firmada antes del análisis
        analysis_result = self.analyze_image(presigned_url)

        if analysis_result:
            # Guardar el resultado en la respuesta de la tarea
            
            task.state = 'completed'

            # Obtener el código del producto o "desconocido" si no está presente
            product = analysis_result.get("Product Code", "desconocido")
            description=analysis_result.get("Description", "desconocido")
            task.response = description
            self.historial.append({"role": "assistant", "content": f"Se recibió una imagen del producto {product}"})
        else:
            task.response = "No se pudo analizar la imagen."
            task.state = 'failed'
            print("No se pudo analizar la imagen.")
