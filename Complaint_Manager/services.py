from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ComplaintManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")
        