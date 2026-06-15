from ninja_extra import ControllerBase, api_controller, http_post, http_get, http_delete
from ninja import File, UploadedFile, Form
from django.db import transaction
from .schemas import DocumentIn, DocumentOut
from myapi.rag_pipeline.docs_processing import document_processing
from .models import Document, DocumentChunk
from myapi.rag_pipeline.docs_processing import document_processing
from myapi.rag_pipeline.embedding import EmbeddingService
from myapi.rag_pipeline.file_type_validator import detect_file_type
from backend.config import settings
from myapi.rag_pipeline.retrieval_Service import HybridRetrievalRerankService
from myapi.agent.graph import create_receptionist_agent
import logging
from langchain_core.messages import HumanMessage
from twilio.twiml.messaging_response import MessagingResponse
from django.http import HttpResponse
from .archive_and_delete import archive_and_delete_document


receptionist_agent= create_receptionist_agent()
embedder= EmbeddingService()
hybrid_retrieval= HybridRetrievalRerankService()



@api_controller("/Twilio", tags= ['Webhook'])
class TwilioWebHookController(ControllerBase):
    @http_post("/whatsapp")
    def whatsapp_webhook(self, request):
        
        incoming_msg= request.POST.get("Body")

        phone= request.POST.get("From")
        if phone.startswith("whatsapp:"):
            phone = phone.replace("whatsapp:", "")

        print("Whatsapp Message:", incoming_msg)
        print("Phone:", phone)

        session_id= phone

        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        initial_state= {
            "query": incoming_msg,
            "user_phone": phone,
            "messages": [HumanMessage(content=incoming_msg)],
        }

        try:
            final_state= receptionist_agent.invoke(initial_state, config= config)

            response_text= final_state.get("clinic_response", "Something went Wrong")

        except Exception as e:
            print("Twilio error:", str(e))

            response_text= (
                "There was problem processing your request"
            )
        twilio_response= MessagingResponse()

        twilio_response.message(response_text)

        return HttpResponse(
            str(twilio_response),
            content_type= "text/xml"

        )

@api_controller("/documents", tags= ['docs'])
class DocumentOperationController(ControllerBase):


    @http_post("/", response= DocumentOut)
    def upload_docs(self, request, data: Form[DocumentIn], docs: File[UploadedFile]):
        
        file_type= detect_file_type(docs)
        
        with transaction.atomic():
            payload= data.model_dump()

            document= Document.objects.create(
                                              status= "PROCESSING",
                                              document= docs,
                                              file_type= file_type,
                                              **payload
                                              )
            
            # Processing
            document_processing(document.id)
            
        return document
    
    @http_delete("/delete/{document_id}")
    def delete_document(self, request, document_id: int):

        document = Document.objects.get(id=document_id)
        archive_and_delete_document(document)

        return {
            "message": "Document deleted successfully"
        }
    
    # For frontend for total docs and total chunks
    @http_get("/stats")
    def document_stats(self, request):

        total_docs = Document.objects.count()

        total_chunks = DocumentChunk.objects.count()

        return {
            "documents": total_docs,
            "chunks": total_chunks
        }
    
    # this is for front end to display all docs 
    @http_get("/")
    def get_documents(self, request):

        docs = Document.objects.all().order_by("-uploaded_at")

        return [
            {
                "id": doc.id,
                "doc_name": doc.doc_name,
                "status": doc.status,
                "file_type": doc.file_type,
                "uploaded_at": doc.uploaded_at
            }
            for doc in docs
        ]
    
    
    @http_get("/status")
    def document_processing_status(self, request, doc_id: int):
        document= Document.objects.get(id= doc_id)
        return {
            "doc_id": document.id,
            "doc_name": document.doc_name,
            "status": document.status
        }


@api_controller("/query", tags= ['Chatbot'])
class ChatOperationController(ControllerBase):
    
    @http_get("/receptionist")
    def agent(self, request, query: str, phone: str):
        print("starting to call agent")

        session_id = phone
        config= {"configurable": {"thread_id": session_id}}

        initial_state = {
            "query": query,
            "user_phone": phone,
            "messages": [HumanMessage(content=query)],
        }

        try: 
            final_state= receptionist_agent.invoke(initial_state, config= config)
            response= final_state.get("clinic_response")
            booking_data= final_state.get("booking_data")
            reschedule_data= final_state.get("reschedule_data")
            print("Agent Ran Successfully.")


            return {
                "response": response,
                "booking_data": booking_data,
                "reschedule_data": reschedule_data
            }
        
        except Exception as e:
            logger= logging.getLogger(__name__)
            logger.error(f"Agent Execution Error: {str(e)}", exc_info= True)

            return {
                "message": "There is problem while running Agent",
                "deatils": str(e) if settings.debug else "Internal Server Error"
            }
        
@api_controller("/pingpong", tags= ['Alive'])
class PingPongOperationController(ControllerBase):
    @http_get("/ping")
    def ping(self, request):
        return {"response": "pong"}
