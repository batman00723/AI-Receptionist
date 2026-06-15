from backend.config import settings
from langchain_groq import ChatGroq
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.model= ChatGroq(
            api_key= settings.groq_api_key.get_secret_value(),
            model= "meta-llama/llama-4-scout-17b-16e-instruct",
            temperature= 0.5,
            max_tokens= 200
        )
    def invoke(self, messages):
        response= self.model.invoke(messages)
        return response
    
    def get_structured(self, schema, messages):
        structured_model = self.model.with_structured_output(schema)
        return structured_model.invoke(messages)
    


    
    