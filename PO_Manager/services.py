from openai import OpenAI
from django.http import JsonResponse
import json
import os
import logging

logger = logging.getLogger(__name__)

class PurchaseOpportunity:
    def __init__(self, client=None):
        self.person = None
        self.product = None
        self.amount = None
        self.historial = []
        self.client = client or OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.products_string = ""
        self.prompt = None
        self.state = {"cantidad": None, "producto": None}
        
        response = self.load_data()
        if isinstance(response, JsonResponse):
            logger.error(response.content.decode())
            return 
        
        self.prompt = (
            f"Eres un experto extrayendo información de conversaciones. "
            f"Extrae las variables importantes (cantidad y producto) y devuélvelas en formato JSON. "
            f"Tu rol NO es devolver documentos. Producto solo puede ser igual a {self.products_string}. "
            f"En caso de que pregunte el precio de algun producto responde que esta información está restringida. "
            f"NO PIDAS CONFIRMACIÓN."
        )

    def load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path) as f:
                data = json.load(f)
                self.products = data.get("products", [])
                self.products_string = ", ".join(self.products)
            self.historial = [{"role": "system", "content": "Eres un asistente que reúne parámetros."}]
        except FileNotFoundError:
            return JsonResponse({'error': "The file 'data.json' was not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': "The file 'data.json' contains invalid JSON."}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while loading data: {str(e)}"}, status=500)
        return None

    def extract_variables(self, conversation):
        if not isinstance(conversation, str) or not conversation.strip():
            logger.error("Invalid conversation input")
            return JsonResponse({'error': "Invalid conversation input."}, status=400)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": conversation.strip()}
                ],
                max_tokens=200,
                n=1,
                stop=None,
                temperature=0.5,
            )
            generated_text = response.choices[0].message.content
            logger.debug(f"Generated text: {generated_text}")
            return generated_text
        
        except Exception as e:
            logger.error(f"Error during API call: {str(e)}")
            return JsonResponse({'error': f"Error during API call: {str(e)}"}, status=500)

    def reset_state(self):
        self.state = {"cantidad": None, "producto": None}
        logger.debug("State has been reset")

    def update_state(self, extracted_params):
        try:
            logger.debug(f"Extracted parameters: {extracted_params}")
            cleaned_params = extracted_params.strip('```json').strip()
            data = json.loads(cleaned_params)
            
            for key in self.state:
                if key in data and data[key]:
                    self.state[key] = data[key]
        except json.JSONDecodeError as e:
            self.state["producto"] = "DIF"
            logger.error(f"Invalid JSON response: {e}")
            logger.error(f"Invalid content: {cleaned_params}")

    def resolve_task(self, task, entry):
        task.update_state('in_progress')
        self.load_data()

        parameters = self.extract_variables(entry)
        self.update_state(parameters)

        if self.state['cantidad'] is None or self.state['producto'] is None:
            missing_params = []
            if self.state['cantidad'] is None:
                missing_params.append("cantidad")
            if self.state['producto'] is None:
                missing_params.append("producto")
                
            if self.state['producto'] == "DIF":
                task.set_response(parameters + "por favor rellene el siguiente formulario: https://forms.gle/DuDpWEnx5GTUn5qYA")
                task.update_state('completed')
                return
            
            missing_params_str = ", ".join(missing_params)
            task.set_response(f"Faltan los siguientes parámetros: {missing_params_str}. Por favor, proporcione la información. O rellene el siguiente formulario: https://forms.gle/DuDpWEnx5GTUn5qYA")
            task.update_state('incomplete')
        else:
            additional_context = f"Notificamos a nuestro equipo de tu interes por {self.state['cantidad']} de {self.state['producto']}, pero si quiere puede registrarlo siguiendo el link: https://forms.gle/DuDpWEnx5GTUn5qYA"
            task.set_response(additional_context)
            task.update_state('completed')
            self.reset_state()