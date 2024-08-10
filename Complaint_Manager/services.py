from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import openai
import os

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class ComplaintDetails(BaseModel):
    # date_of_complaint_reception: str = Field(
    #     "",
    #     description="Date of self.complaint reception by distributor"
    # )
    date_of_occurrence: str = Field(
        "",
        description="Date of occurrence (according to the complainant)"
    )
    contact_name: str = Field(
        "",
        description="Name of contact"
    )
    hospital_name: str = Field(
        "",
        description="Hospital/Institution name"
    )
    # hospital_address: str = Field(
    #     "",
    #     description="Hospital/Institution address"
    # )
    # contact_phone: str = Field(
    #     "",
    #     description="Contact phone number"
    # )
    contact_email: str = Field(
        "",
        description="Contact e-mail address"
    )
    product_code: str = Field(
        "",
        description="Product code (SKU)"
    )
    # gtin_udi: str = Field(
    #     "",
    #     description="GTIN/UDI"
    # )
    batch_number: str = Field(
        "",
        description="Batch number"
    )
    # serial_number: str = Field(
    #     "",
    #     description="Serial number"
    # )
    failure_description: str = Field(
        "",
        description="Description of the failure, unusual result or performance"
    )
    # additional_details: str = Field(
    #     "",
    #     description="Additional details about the circumstances in which the failure occurred"
    # )
    # defective_units: int = Field(
    #     0,
    #     description="Amount of defective units"
    # )
    # total_units: int = Field(
    #     0,
    #     description="Total amount of units used (including defective and not-defective units)"
    # )
    # photographic_evidence: str = Field(
    #     "",
    #     description="Photographic evidence"
    # )
    # file_attachments: str = Field(
    #     "",
    #     description="Field or button to attach files (except videos)"
    # )
    # video_links: str = Field(
    #     "",
    #     description="Videos links"
    # )
    video_url: str = Field(
        "",
        description="Please, share the URL for videos"
    )

    def __init__(self, **data):
        super().__init__(**{**{field: "" if field != "defective_units" and field != "total_units" else 0 for field in self.__fields__}, **data})

class ComplaintManager:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.complaint = ComplaintDetails()
            self.assistant_id = os.getenv('COMPLAINT_ASSISTANT_ID')
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading data: {str(e)}")
    
    def check_what_is_empty(self, complaint_details_form):
        ask_for = []
        for field, value in complaint_details_form.dict().items():
            if value in [None, "", 0]:
                ask_for.append(f'{field}')
        return ask_for

    def add_non_empty_details(self, current_details: ComplaintDetails, new_details: ComplaintDetails):
        for field, value in new_details.dict().items():
            if value not in [None, ""]:
                setattr(current_details, field, value)
        print("current_details actualizado: ")
        print(current_details)

    def create_tagging_chain_pydantic(self, model, ask_for):
        fields_text = ", ".join(ask_for)
        
        def extract_fields(text):
            prompt = (
                f"Extract the following information from the user's input and map it to the appropriate fields: {fields_text}\n\n"
                f"User input: {text}\n\n"
                f"Extracted fields:"
            )

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            extracted_info = response.choices[0].message.content
            return extracted_info
        
        return extract_fields

    def ask_for_info(self, ask_for,query, thread):

        chat = self.client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            # role= "system", content= f"Below are some things to ask the user for in a conversational way. You should only ask one question at a time even if you don't get all the info. Don't ask as a list! Don't greet the user! Don't say Hi. Explain you need to get some info. If the ask_for list is empty then thank them and ask how you can help them. ask_for list: {ask_for}",
            role="user", content=f"{query}"
            )
        run = self.client.beta.threads.runs.create_and_poll(
        thread_id=thread.thread_id,
        assistant_id=self.assistant_id,
        instructions=f"Below are some things to ask the user for in a conversational way. You should only ask one question at a time even if you don't get all the info. Don't ask as a list! Don't greet the user! Don't say Hi. Explain you need to get some info. If the ask_for list is empty then thank them and ask how you can help them. ask_for list: {ask_for}"
        )
        if run.status == 'completed': 
            messages_response = self.client.beta.threads.messages.list(
                thread_id=thread.thread_id                     )
        else:
            print(run.status)
        messages = messages_response.data
        latest_message = messages[0]    
        if messages and hasattr(latest_message, 'content'):
            content_blocks = messages[0].content
            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                text_block = content_blocks[0]
                if hasattr(text_block, 'text') and hasattr(text_block.text, 'value'):
                    ai_chat=   text_block.text.value
                    
                                                
        # instructions="Please address the user as Jane Doe. The user has a premium account."
        
        # prompt = (
        #     "Below are some things to ask the user for in a conversational way. You should only ask one question at a time even if you don't get all the info. "
        #     "Don't ask as a list! Don't greet the user! Don't say Hi. Explain you need to get some info. If the ask_for list is empty then thank them and ask how you can help them.\n\n"
        #     f"### ask_for list: {ask_for}"
        # )

        # response = openai.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful assistant."},
        #         {"role": "user", "content": prompt}
        #     ]
        # )

        # ai_chat = response.choices[0].message.content
        return ai_chat

    def filter_response(self, text_input, complaint_details_form):
        ask_for = self.check_what_is_empty(complaint_details_form)
        extract_fields = self.create_tagging_chain_pydantic(ComplaintDetails, ask_for)
        extracted_info = extract_fields(text_input)
        extracted_info_dict = {field.split(':')[0].strip().strip("'"): field.split(':')[1].strip().strip("'") for field in extracted_info.split('\n') if ':' in field}
        new_details = ComplaintDetails(**extracted_info_dict)
        self.add_non_empty_details(complaint_details_form, new_details)
        ask_for = self.check_what_is_empty(complaint_details_form)
        return ask_for

    def handle_complaint(self, query, task,thread):
        
        task.update_state('in_progress')
        print("state adentro del handle")
        print(task.get_state())
        ask_for = self.filter_response(query, self.complaint)
        ai_response = self.ask_for_info(ask_for,query, thread)
        print(query)
        print(ai_response)
         # Depuración para ver qué se está solicitando
        # print("Campos solicitados: ", ask_for)
        if not ask_for:
                ai_response = 'Everything gathered, move to next phase'
                print("AI response: " + ai_response)
                task.set_response(ai_response)
                task.update_state('completed')
                print("no hay mas askfor")
        else:
            print(type(ai_response))
            task.set_response(ai_response)
            

        # task.set_response(ai_response)
        return 0
        # ask_for = self.check_what_is_empty(self.complaint)

        # if ask_for:
            
        #     print("AI response: " + ai_response)

        # while ask_for:
        #     text_input = query  # Aquí se asume que el input viene de la interacción del chatbot
            

            

        

        
