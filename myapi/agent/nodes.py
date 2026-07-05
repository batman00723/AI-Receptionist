from pydantic import BaseModel, Field
from .state import ReceptionistState
from backend.config import settings
from myapi.rag_pipeline.llm import ChatLLMService, RoutingLLMService
from langgraph.graph import END
from myapi.rag_pipeline.embedding import EmbeddingService
from myapi.rag_pipeline.retrieval_Service import HybridRetrievalRerankService
from langchain_core.messages import SystemMessage, HumanMessage, trim_messages, AIMessage
from typing import Optional
from myapi.agent.cal_service import CalService      
from myapi.agent.email_service import send_emergency_alert, send_cancellation_alert
from typing import Literal
from datetime import datetime
import pytz
import dateparser
from myapi.models import Patient, Appointment
from .utc_2_ist import utc_to_ist
from myapi.rag_pipeline.semantic_cache import save_to_db, semantic_cache_search


class RouteResponse(BaseModel):
    intent: Literal[ "booking", "cancel", "show_booking", "faq", "emergency", "nonsense", "reschedule", "completed"] = Field(
        description="Categorize the user's query into: 'faq', 'booking', 'cancel', 'reschedule', 'emergency', or 'nonsense'."
    )
    # confidence: float = Field(
    #     description="A score between 0.0 and 1.0 reflecting how sure you are of this intent."
    # )



route_llm= RoutingLLMService()
chatllm = ChatLLMService()
embedder = EmbeddingService()
hybrid_retrieval= HybridRetrievalRerankService()


def router_node(state: ReceptionistState):
    message_history= state["messages"][-4:]
    print(f"Message_History_router_node: {message_history}")
    
    query= state["query"]


    if not message_history:
        return {"query": query }
    
    if state.get("active_workflow") == "booking" and state.get("missing_booking_fields"):
        return {
            "intent": "booking",
            "query": query
        }
    if state.get("active_workflow") == "reschedule" and state.get("missing_reschedule_fields"):
        return {
            "intent": "reschedule",
            "query": query
        }
    
    system_instruction = f"""
        You are a strict intent classification router for a dental clinic AI system.

        Your job is ONLY to classify the user's latest message into ONE category.

        Valid categories:
        - booking
        - faq
        - emergency
        - nonsense
        - reschedule
        - cancel
        - show_booking

        IMPORTANT:
        Use BOTH:
        1. latest user message
        2. recent conversation context
        
        ROUTING RULES:

        1. booking
        Use booking if:
        - user wants to book appointment
        - user provides booking details:
        date, time, doctor, treatment
        - assistant previously asked for missing booking information and user is replying with partial info

        Examples:
        - "Friday"
        - "2 pm"
        - "yes book it"
        - "next monday"
        - "11 am"
        - "book"

        2. emergency
        Use ONLY for urgent medical situations:
        - severe pain
        - swelling
        - bleeding
        - broken tooth
        - infection
        - trauma
        - medical emergency
        - life threatening situation

        DO NOT classify normal dental questions as emergency.

        3. faq
        Use for:
        - if someone greets
        - insurance
        - pricing
        - clinic timings
        - procedures
        - treatments
        - location
        - dental questions
        - services offered
        - asking about dental questions
        - asking about the clinic, any question realted to clinic

        Examples:
        - "Do you offer root canal?"
        - "What insurance do you accept?"
        - "Where are you located?"

        4. nonsense
        Use if:
        - random/off-topic message
        - unclear meaning
        - abusive message without actionable intent
        - confidence is low
 
        Examples:
        - madarchod
        - betichod
        - tum chutiya ho
        - Who won the IPL?
        - Write me a poem.
        - What's the capital of France?

        5. cancel
        Use if:
        - user wants to cancel their appointment.
        - user wants to cancel their existing appointment
        - user explicitly says to cancel their booking.
        - user says to cancel booking
        - user says to cancel booking, appointment

        Examples:
        - "Cancel my appointment"
        - "Cancel my current booking"
        - "Cancel my current appointment"
        - "Cancel it"

        6. reschedule
        Use if:
        - user wants to move an appointment
        - user wants a different date
        - user wants a different time

        Examples:
        - reschedule my appointment
        - move my appointment
        - change my booking
        - can I come next Friday instead

        7. show_booking
        Use if user wants to:
        - view appointment
        - check appointment
        - know booking details
        - know appointment date
        - know appointment time

        CRITICAL RULES:

        - NEVER hallucinate missing intent.
        - If uncertain, choose nonsense.
        - If booking workflow is already active, prioritize booking classification.
        - Single-word replies like "Friday" or "2 pm" are booking ONLY if conversation context indicates active booking flow.
        - Do NOT overthink.
        - Output ONLY the category name.

        For Context of router use the previous conversation history to route correctly

    """
    
    message_for_llm= [SystemMessage(content= system_instruction)] + message_history

    if not message_history or message_history[-1].content != query:
        message_for_llm.append(HumanMessage(content=f"User's current request: {query}"))


    try:
        structured_llm = route_llm.model.with_structured_output(RouteResponse)
        response = structured_llm.invoke(message_for_llm)
        intent = response.intent
        print(intent)
        # print(response.confidence)
        # if response.confidence < 0.6:
        #     intent= "nonsense" 
    except Exception as e:
        print(f"Router Error: {e}")
        intent = "faq"
    
    return{
        "intent": intent,
        "query": query
    }

def routing_logic(state: ReceptionistState):
    intent= state["intent"]
    if intent == "emergency":
        return "emergency_escalation"
    elif intent == "faq":
        return "knowledge_base"
    elif intent == "booking":
        return "appointment_manager"
    elif intent == "cancel":
        return "cancel_booking"
    elif intent == "show_booking":
        return "show_booking"
    elif intent == "reschedule":
        return "reschedule_booking"
    else:
        return "refusal_node"
    



def faq_node(state: ReceptionistState):
    print("FAQ Node Activated")
    message_history = state["messages"][-10:]
    
    current_intent= state["intent"]
    print(current_intent)
    
    query= state["query"]

    query_vector= embedder.get_embedding(query)

    CACHEABLE_MIN_WORDS = 8

    use_cache = len(query.split()) >= CACHEABLE_MIN_WORDS

    if use_cache:
        cached = semantic_cache_search(query_vector)

        CACHE_THRESHOLD = 0.05

        if cached and cached.distance < CACHE_THRESHOLD:
            print("SEMANTIC CACHE HIT")
            print(f"Distance: {cached.distance}")

            return {
                "messages": [AIMessage(content=cached.response)],
                "clinic_response": cached.response
            }


    print("SEMANTIC CACHE MISS")


    top_chunks= hybrid_retrieval.get_hybrid_reranked_content(query= query, query_vector= query_vector)

    content_chunks = "\n\n".join([c.chunk for c in top_chunks])

    system_prompt = f"""
        You are the AI booking and information assistant for Caps and Crowns Dental Clinic.

        Your job is to:
        - Answer clinic-related questions
        - Assist with basic dental service information
                                  
        Keep answers under 100 words unless the user explicitly asks for more detail.

        Your tone should be:
        - Professional
        - Calm
        - Reassuring
        - Concise
        
        Speak like a friendly dental receptionist chatting with a patient on WhatsApp.
        Use natural conversational language.
        Avoid sounding like a textbook, FAQ page, or medical article.

        # KNOWLEDGE BASE
        You have access to the Caps and Crowns Dental Clinic knowledge base.
        Use it to answer questions related to:
        - Dental cleanings
        - Consultations and exams
        - Crowns and caps
        - Fillings
        - Root canals
        - Teeth whitening
        - Cosmetic dentistry
        - Emergency dental visits
        - Insurance and payment information
        - Office hours
        - Clinic location
        - Appointment policies
        - Post-treatment instructions

        Only answer using the provided clinic knowledge.

        If information is unavailable:
        - do not guess
        - do not hallucinate
        - politely say I don't know                                  
        
        If user greets, greet back nicely and be chatty and don't sound robotic. 

        Use the context only as a source of facts.
        Do not copy phrases directly from the context unless necessary.
        Rewrite answers naturally for a patient chatting on WhatsApp.
    
        "Before ending the conversation ask a followup question if there is need for it."
        Only ask a follow-up question when appropriate.
                                                            
        If no:
        "Thank you for choosing Caps and Crowns Dental Clinic. Have a wonderful day!"
                                  
        Also use the Conversation history for previous context.
        When the user asks a follow-up question such as:
        "how much?"
        "what about Sunday?"
        "and whitening?"
        "how long does it take?"

        Use the Conversation History to determine what they are referring to,
        or If the user asks a follow-up question, use the conversation history to understand what they are referring to.                               
                                     
        USER QUERY:
        {query}
        
        CONTEXT:
        {content_chunks}

        """
        
    
    messages_for_llm = [SystemMessage(content=system_prompt)] + message_history
    
    response= chatllm.invoke(messages_for_llm).content

    save_to_db(query= query,
               query_embedding= query_vector,
               response= response)
    
    return{
        "messages": [AIMessage(content= response)],
        "clinic_response": response
    }



def refusal_node(state: ReceptionistState):
    print("Refusal Node Activated")
    response = (
        "I'm not sure I can help with that. I can assist with appointments, our clinic information, or dental-related questions.😊"
    )
    
    return {
        "messages": [AIMessage(content=response)],
        "clinic_response": response
    }
    
from datetime import datetime, timedelta
import pytz
import dateparser

class BookingExtraction(BaseModel):
    date_phrase: Optional[str] = Field(
        default= None,
        description= "Raw date phrase exactly as user said it. Example: tomorrow, next Friday may 20"
    )
    time_phrase: Optional[str]= Field(
        default= None,
        description= "Raw time phrase as exactly as user said it. Example: 2pm, 10:30 pm"
    )
    service: Optional[str] = Field(
        default=None,
        description="Dental service requested by user"
    )


def booking_node(state: ReceptionistState):

    tz_ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz=tz_ist)

    current_booking = state.get("booking_data") or {}
    query = state["query"]

    print("CURRENT BOOKING STATE")
    print(current_booking)

    structured_llm = route_llm.model.with_structured_output(
        BookingExtraction

    )
    system_prompt = f"""
        You are a strict booking information extraction system.

        Your ONLY job is to extract structured booking fields from the user's latest message.

        Extract:
        - date_phrase
        - time_phrase
        - service

        IMPORTANT:
        - Extract ONLY explicitly mentioned information.
        - NEVER infer missing fields.
        - NEVER guess.
        - NEVER calculate actual dates.
        - NEVER rewrite values.
        - Return raw user phrases exactly as written.
        - Use recent conversation context ONLY to understand references, not to invent values.

        FIELD RULES:

        1. date_phrase
        Extract ONLY:
        - weekdays
        - dates
        - relative dates
        - booking day references

        Examples:
        - "Friday"
        - "next monday"
        - "tomorrow"
        - "May 22"

        DO NOT extract:
        - treatment names
        - generic booking phrases
        - unrelated text

        2. time_phrase
        Extract ONLY explicit times.

        Examples:
        - "2 pm"
        - "11:30"
        - "morning"
        - "afternoon"

        DO NOT infer times.

        3. service
        Extract ONLY explicitly mentioned dental services.

        Examples:
        - "root canal"
        - "Invisalign"
        - "cleaning"

        DO NOT infer service from context.

        CONTEXT RULES:

        - If user says:
        "yes book it"
        → DO NOT invent missing fields.

        - If user says:
        "Friday at 2 pm"
        → extract both.

        - If user only says:
        "2 pm"
        → extract ONLY time_phrase.

        - If a field is not explicitly present in latest message:
        return null for that field.


        Return ONLY valid JSON.

        Do not infer any booking details on your own unless user provides it.
        If user gives wrong spelling of week days for example Frday so make it Friday.
        Only use you intelligence to make spellings correct for date time and service names for dental clinic.
    """


    messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=query)
    ]

    extraction = structured_llm.invoke(messages)


    print("Raw Extracted Booking Data")
    print(extraction)

    def clean(value):

        if not value:
            return None

        value = value.strip().lower()
        invalid = {
            "",
            "null",
            "none",
            "unknown",
            "n/a",
        }
        return None if value in invalid else value

    raw_date = clean(extraction.date_phrase)
    raw_time = clean(extraction.time_phrase)
    raw_service = clean(extraction.service)




    effective_date = raw_date or current_booking.get("date")
    effective_time = raw_time or current_booking.get("time")
    effective_service = (
        raw_service or current_booking.get("service")
    )

    weekday_map = {
    "next monday": "monday",
    "next tuesday": "tuesday",
    "next wednesday": "wednesday",
    "next thursday": "thursday",
    "next friday": "friday",
    "next saturday": "saturday",
    "next sunday": "sunday",
    }

    effective_date = weekday_map.get(effective_date, effective_date)

    updated_booking = {
        "date": effective_date,
        "time": effective_time,
        "service": effective_service,
        "utc_time": current_booking.get("utc_time"),
    }

    if effective_date and effective_time:

        combined_text = (
            f"{effective_date} {effective_time}"
        )
        print("COMBINED TEXT")
        print(repr(combined_text))

        parsed_dt = dateparser.parse(
            combined_text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now_ist,
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )

        if parsed_dt:

            updated_booking["date"] = (
                parsed_dt.strftime("%Y-%m-%d")
            )
            updated_booking["time"] = (
                parsed_dt.strftime("%H:%M")
            )
            utc_dt = parsed_dt.astimezone(
                pytz.utc
            )
            updated_booking["utc_time"] = (
                utc_dt.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                )
            )

            print("IST:", parsed_dt)

            print(
                "UTC:",
                updated_booking["utc_time"]
            )


            print("Raw extraction:", extraction)
            print("Combined text:", combined_text)
            print("Parsed datetime:", parsed_dt)
            print("UTC datetime:", parsed_dt.astimezone(pytz.utc) if parsed_dt else None)
        else:

            print("Date parsing failed")

    return {
        "booking_data": updated_booking,
        "active_workflow": "booking"
    }

def booking_validate_node(state: ReceptionistState):

    booking = state.get("booking_data") or {}
    
    missing = []

    if not booking.get("date"):
        missing.append("date")
    if not booking.get("time"):
        missing.append("time")
    if not booking.get("service"):
        missing.append("service")
    print("BOOKING STATE INSIDE VALIDATION")
    print(booking)

    return {
        "missing_booking_fields": missing,
        "active_workflow": "booking"
    }

def booking_validation_router(state: ReceptionistState):
    missing= state.get("missing_booking_fields", [])

    if missing:
        return "booking_followup"
    
    return "check_availability"

def booking_followup_node(state: ReceptionistState):
    missing= state.get("missing_booking_fields", [])

    prompt_map = {
        "date": "What day would you like to come in?. Note that we are closed on Sunday.📅",
        "time": "What time works best for you?🕒. Please mention AM or PM.",
        "service": "What service are you looking for? Cleaning, Root Canal, Genral Consultation🦷"
    }

    response_text= prompt_map[missing[0]]

    return {
        "messages": [AIMessage(content= response_text)],
        "clinic_response": response_text,
        "active_workflow": "booking"
    }


def check_availabiity_node(state: ReceptionistState):
    cal= CalService()
    booking= state["booking_data"]
    print("BOOKING TIME:", booking["time"])
    print("BOOKING ATTEMPT")
    print(booking)

    print("ACTIVE APPOINTMENT")
    print(state.get("active_appointment") or {})

    try:
        print(booking["date"])
        available_slots= cal.get_slots(booking["date"])
        print("AVAILABLE SLOTS:", available_slots)
        is_available = any(booking["utc_time"] == slot["time"] for slot in available_slots)

        if is_available:
            booking_response= cal.create_booking(booking, {"phone": state.get("user_phone", "000000")})
            final_message= f"You are all set! Your appointment with Dr. Mishra has been booked for {booking['time']} on {booking['date']} 🎉. We are looking forward to seeing you!"
            print(f"Booking Response: {booking_response}")

            
            # Create patient record in patient table and also in Appointment table
            patient, _ = Patient.objects.get_or_create(phone=state["user_phone"])
            Appointment.objects.create(
                patient=patient,
                booking_uid=booking_response["data"]["uid"],
                booking_id=booking_response["data"]["id"],
                service=booking["service"],
                date=booking["date"],
                time=booking["time"],
                status="scheduled"
            )

            return {"clinic_response": final_message, "intent": "completed", "booking_data": None, "missing_booking_fields": [], "active_workflow": None,  "active_appointment": {

                                                                                                                                                            "booking_uid": booking_response["data"]["uid"],
                                                                                                                                                            "booking_id": booking_response["data"]["id"],
                                                                                                                                                            "date": booking["date"],
                                                                                                                                                            "time": booking["time"],
                                                                                                                                                            "service": booking["service"]
                                                                                                                                                            }}
        
        else:
            available_ist_slots = [utc_to_ist(slot["time"]) for slot in available_slots]
            
            # MVP Naive fail message will change it later and add neaerest slots available instead of hard slots
            fail_message = f"Unfortunately 😔! This exact time slot is not available, By the way these slots are available try these instead: {', '.join(available_ist_slots)}"
            return {"clinic_response": fail_message, "intent": "booking", "active_workflow": "booking"}
    except Exception as e:
        # If api is down then manual entry by human receptionist.
        error_message= "There is technical glitch, but don't worry I have informed your booking details to my supervisor he will handle and send you conformation messge soon.. and please check your phone number..."
        print(e)
        return {"clinic_response": error_message, "intent": "emergency", "active_workflow": None}
    

def emergency_node(state: ReceptionistState):
    phone= state.get("user_phone", "No Phone provided")
    issue= state.get("query", "No issue provided")

    send_emergency_alert(patient_phone= phone,
                         patient_issue= issue)

    emergency_message= (
        "I have notified an urgent alert to my Supervisor they will handle this critical situation." \
        "They will call you immediately. If it is life threatning," \
        "Please call your local emergency services.🚨"
    )

    return {
        "messages": [AIMessage(content=emergency_message)],
        "clinic_response": emergency_message
    }


def cancel_booking_node(state: ReceptionistState):
    print("Entered Cancel Booking Node" \
    "")
    appointment= state.get("active_appointment")
    print(f"Active Appointment: {appointment}")
    
    if not appointment:
        response= ( "I'm Sorry 😔, I couldn't find any of your active appointment to cancel")
        
        return {"clinic_response": response, "messages": [AIMessage(content= response)]}
    
    cal= CalService()

    try:
        result= cal.cancel_booking(
            appointment["booking_uid"]
        )
        print(result)
        
        # Update Appointment table 
        Appointment.objects.filter(booking_uid=appointment["booking_uid"]).update(status="cancelled")

        response= f"Your appointment on {appointment['date']} at {appointment['time']} has been cancelled successfully.😊"

        return{
            "clinic_response": response,
            "messages": [
                AIMessage(content=response)
            ],
            "active_appointment": {},
            "booking_data": None,
            "active_workflow": None,
            "intent": "completed"
        }
    except Exception as e:
        print(e)

        try:
            send_cancellation_alert(
                patient_phone= state["user_phone"],
                patient_issue= appointment
            )

            response= "Looks like there is a techincal glitch, I have send your cancellation request to my supervisor. Don't worry he will handle it now."


            return {
            "clinic_response": response,
            "messages": [
                AIMessage(content=response)
            ],
            "active_workflow": None,
            "intent": "completed"
            }
        
        except Exception as e:

            print(e)

            return {"clinic_response": "There was a technical issue processing your cancellation request. Please contact the clinic directly.",
                    "intent": "completed",
                    "active_workflow": None}
        
    
def show_booking_node(state: ReceptionistState):
    appointment= state.get("active_appointment")

    print(f"Active Appointment: {appointment}")

    if not appointment:
        response = (
            "It seems like you don't have any active appointment."
        )
        return {
            "clinic_response": response,
            "messages": [AIMessage(content= response)]
        }
    
    response= (
        f"You have an appointment scheduled on "
        f"{appointment['date']} at "
        f"{appointment['time']} for "
        f"{appointment['service']}"
        f"See you there."
    )
    return {
        "clinic_response": response,
        "messages": [AIMessage(content= response)]
        }

# This node is just a passthrough as langgraph needs a entry function for making an conditional edge
def check_active_booking_node(state):
    return {}

def check_active_booking_router(state: ReceptionistState):
    if state.get("active_appointment"):
        return "reschedule"    
    return "no_booking"


def no_booking_response(state: ReceptionistState):
    response= "I'm Sorry!😔, but you don't have any active booking to reschedule."
    return {
        "clinic_response": response,
        "messages": [AIMessage(content= response)]
    }



class RescheduleExtraction(BaseModel):
    date_phrase: Optional[str] = Field(
        default= None,
        description= "Raw date phrase exactly as user said it. Example: tomorrow, next Friday may 20"
    )
    time_phrase: Optional[str]= Field(
        default= None,
        description= "Raw time phrase as exactly as user said it. Example: 2pm, 10:30 pm"
    )


def reschedule_node(state: ReceptionistState):
    appointment = state.get("active_appointment")
    if not appointment:
        response= "Seems like you don't have any appointment scheduled to reschedule."
        return {
            "clinic_response": response,
            "messages": [AIMessage(content=response)],
            "intent": "completed",
            "active_workflow": None
        }
    
    print("ACTIVE APPOINTMENT")
    print(state.get("active_appointment"))


    tz_ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz=tz_ist)

    rescheduled_booking = state.get("reschedule_data") or {}
    query = state["query"]

    structured_llm = route_llm.model.with_structured_output(
        RescheduleExtraction
    )

    system_prompt = f"""
        You are a strict booking information extraction system.

        Your ONLY job is to extract structured booking fields from the user's latest message.

        Extract:
        - date_phrase
        - time_phrase

        IMPORTANT:
        - Extract ONLY explicitly mentioned information.
        - NEVER infer missing fields.
        - NEVER guess.
        - NEVER calculate actual dates.
        - NEVER rewrite values.
        - Return raw user phrases exactly as written.
        - Use recent conversation context ONLY to understand references, not to invent values.

        FIELD RULES:

        1. date_phrase
        Extract ONLY:
        - weekdays
        - dates
        - relative dates
        - booking day references

        Examples:
        - "Friday"
        - "next monday"
        - "tomorrow"
        - "May 22"

        DO NOT extract:
        - treatment names
        - generic booking phrases
        - unrelated text

        2. time_phrase
        Extract ONLY explicit times.

        Examples:
        - "2 pm"
        - "11:30"
        - "morning"
        - "afternoon"

        DO NOT infer times.


        CONTEXT RULES:

        - If user says:
        "yes book it"
        → DO NOT invent missing fields.

        - If user says:
        "Friday at 2 pm"
        → extract both.

        - If user only says:
        "2 pm"
        → extract ONLY time_phrase.

        - If a field is not explicitly present in latest message:
        return null for that field.

        EXISTING BOOKING STATE:
        {rescheduled_booking}

        USER MESSAGE:
        {query}

        Return only valid JSON

        Do not infer any booking details on your own unless user provides it.
        If user gives wrong spelling of week days for example Frday so make it Friday.
        Only use you intelligence to make spellings correct for date time.

    """

    extraction = structured_llm.invoke(system_prompt)
    print(extraction)

    print("Raw Extracted Reschedule Data")
    print(extraction)

    def clean(value):
        if not value:
            return None

        value = value.strip().lower()
        invalid = {
            "",
            "null",
            "none",
            "unknown",
            "n/a",
        }
        return None if value in invalid else value

    raw_date = clean(extraction.date_phrase)
    raw_time = clean(extraction.time_phrase)

    effective_date = raw_date or rescheduled_booking.get("date")
    effective_time = raw_time or rescheduled_booking.get("time")

    updated_booking = {
        "date": effective_date,
        "time": effective_time,
        "utc_time": rescheduled_booking.get("utc_time"),
    }

    if effective_date and effective_time:

        combined_text = (
            f"{effective_date} {effective_time}"
        )

        parsed_dt = dateparser.parse(
            combined_text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now_ist,
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )

        if parsed_dt:

            updated_booking["date"] = (
                parsed_dt.strftime("%Y-%m-%d")
            )
            updated_booking["time"] = (
                parsed_dt.strftime("%H:%M")
            )
            utc_dt = parsed_dt.astimezone(
                pytz.utc
            )
            updated_booking["utc_time"] = (
                utc_dt.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                )
            )

            print("IST:", parsed_dt)

            print(
                "UTC:",
                updated_booking["utc_time"]
            )
        else:

            print("Date parsing failed")

    return {
        "reschedule_data": updated_booking,
        "active_workflow": "reschedule"
    }

def reschedule_validate_node(state: ReceptionistState):

    reschedule = state.get("reschedule_data") or {}
    
    missing = []

    if not reschedule.get("date"):
        missing.append("date")
    if not reschedule.get("time"):
        missing.append("time")
    print("RESCHEDULE STATE INSIDE VALIDATION")
    print(reschedule)

    return {
        "missing_reschedule_fields": missing,
        "active_workflow": "reschedule"
    }


def reschedule_validation_router(state: ReceptionistState):
    missing= state.get("missing_reschedule_fields", [])
    print(f"Missing reschedule data: {missing}")
    if missing:
        return "reschedule_followup"
    
    return "reschedule_availability"

def reschedule_followup_node(state: ReceptionistState):
    missing= state.get("missing_reschedule_fields", [])

    prompt_map = {
        "date": "What new day you want to come instead?",
        "time": "What new time would you like instead?",
    }

    response_text= prompt_map[missing[0]]

    return {
        "messages": [AIMessage(content= response_text)],
        "clinic_response": response_text,
        "active_workflow": "reschedule"
    }


def check_reschedule_availabiity_node(state: ReceptionistState):
    cal= CalService()
    reschedule= state["reschedule_data"]
    print("Reschedule TIME:", reschedule["time"])
    print("RESCHEDULE ATTEMPT")
    print(reschedule)

    print("ACTIVE APPOINTMENT")
    active_appointment= state["active_appointment"]
    print(state.get("active_appointment") or {})

    try:
        print(reschedule["date"])
        available_slots= cal.get_slots(reschedule["date"])
        print("AVAILABLE SLOTS:", available_slots)
        is_available = any(reschedule["utc_time"] == slot["time"] for slot in available_slots)

        if is_available:
            reschedule_response= cal.reschedule_booking(booking_uid= active_appointment["booking_uid"],
                                                        new_utc_time= reschedule["utc_time"])
            print(reschedule_response)
            final_message= f"You are all set! Your appointment with Dr. Mishra has been rescheduled to {reschedule['time']} on {reschedule['date']} 🎉. See you then!"
            print(f"Booking Response: {reschedule_response}")

            print("OLD APPOINTMENT")
            print(active_appointment)

            print("RESCHEDULE RESPONSE")
            print(reschedule_response)

            print("NEW UID")
            print(reschedule_response["data"]["uid"])

            print("RETURNING ACTIVE APPOINTMENT")

            # Now new booking uid and bookinng id is given to updated booking doct instance and further it will overwrite the stale old data of active appointmet as that active apppointment is not new rescheduled appointemtn
            # and the rescheduled appointment returns new booking uid and id so we put it in active appointment and overwrite old appointment.
            updated_appointment = {
            "booking_uid": reschedule_response["data"]["uid"],
            "booking_id": reschedule_response["data"]["id"],
            "date": reschedule["date"],
            "time": reschedule["time"],
            "service": active_appointment["service"]
            }

            print(updated_appointment)

            # Update appointments table
            Appointment.objects.filter(
                booking_uid=active_appointment["booking_uid"]
            ).update(
                booking_uid=reschedule_response["data"]["uid"],
                booking_id=reschedule_response["data"]["id"],
                date=reschedule["date"],
                time=reschedule["time"]
            )

            return {"clinic_response": final_message, "intent": "completed", "reschedule_data": None, "missing_reschedule_fields": [], "active_workflow": None,  "active_appointment": updated_appointment}
        
        else:
            available_ist_slots = [utc_to_ist(slot["time"]) for slot in available_slots]
            fail_message = f"Unfortunately 😔! This exact time slot is not available, By the way these slots are available try these instead: {', '.join(available_ist_slots)}"
            return {"clinic_response": fail_message, "intent": "reschedule", "active_workflow": "reschedule"}
    except Exception as e:
        # If api is down then manual entry by human receptionist.
        error_message= "There is technical glitch, but I have informed your reschedule booking details to my supervisor he will handle and send you conformation messge soon.."
        print(e)
        return {"clinic_response": error_message, "intent": "emergency", "active_workflow": None}
    


