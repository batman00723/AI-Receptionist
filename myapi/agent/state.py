from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

def merge_dict(existing: dict, new: dict) -> dict:
    """Only updates keys that are actually provided."""
    updated = existing.copy()
    updated.update({k: v for k, v in new.items() if v is not None})
    return updated

class ReceptionistState(TypedDict):
    query: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_phone: str
    intent: str # by router faq, booking or emergency, or nonsense
    # parsed dict by llm for booking to send to calendar api
    booking_data: Annotated[Optional[dict], merge_dict] # eg {"date": "2026-05-12", "time": "14:00", "service": "Cleaning"}
    clinic_response: str # final response for user
    missing_booking_fields: Optional[list]
    active_workflow: Optional[str]

    active_appointment: Annotated[Optional[dict], merge_dict]

    reschedule_data: Annotated[Optional[dict], merge_dict]
    missing_reschedule_fields: Optional[list]
