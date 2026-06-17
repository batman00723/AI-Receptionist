from .nodes import router_node, faq_node, booking_node, emergency_node, refusal_node, check_availabiity_node, routing_logic, booking_followup_node, booking_validate_node, booking_validation_router, cancel_booking_node, show_booking_node, check_reschedule_availabiity_node, reschedule_followup_node, reschedule_node, reschedule_validate_node, reschedule_validation_router, check_active_booking_router, no_booking_response, check_active_booking_node
from langgraph.graph import StateGraph, END
from functools import partial
from .state import ReceptionistState
from backend.config import settings
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver


DB_URL = settings.db_url.get_secret_value()

_pool = ConnectionPool(
    conninfo=DB_URL,
    max_size=10,
    open= True,
    kwargs={"autocommit": True, "prepare_threshold": 0, "connect_timeout": 20} 
)

memory = PostgresSaver(_pool)
memory.setup()

def create_receptionist_agent():
    workflow= StateGraph(ReceptionistState)

    workflow.add_node("router", router_node)
    workflow.add_node("knowledge_base", faq_node)
    workflow.add_node("appointment_manager", booking_node)
    workflow.add_node("booking_validation", booking_validate_node)
    workflow.add_node("booking_followup", booking_followup_node)
    workflow.add_node("availability_node", check_availabiity_node)
    workflow.add_node("emergency_escalation", emergency_node)
    workflow.add_node("refusal_node", refusal_node)
    workflow.add_node("cancel_booking", cancel_booking_node)
    workflow.add_node("show_booking", show_booking_node)
    workflow.add_node("reschedule_booking", reschedule_node)
    workflow.add_node("reschedule_validation", reschedule_validate_node)
    workflow.add_node("reschedule_followup", reschedule_followup_node)
    workflow.add_node("reschedule_availability", check_reschedule_availabiity_node)

    workflow.add_node("reschedule_guard", check_active_booking_node)
    workflow.add_node("no_booking_response", no_booking_response)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        routing_logic,
        {
            "emergency_escalation": "emergency_escalation",
            "knowledge_base": "knowledge_base",
            "appointment_manager": "appointment_manager",
            "refusal_node": "refusal_node",
            "cancel_booking": "cancel_booking",
            "reschedule_booking": "reschedule_guard",
            "show_booking": "show_booking"
        }
    )
    workflow.add_edge("appointment_manager", "booking_validation")

    workflow.add_conditional_edges(
        "booking_validation",
        booking_validation_router,
        {
            "booking_followup": "booking_followup",
            "check_availability": "availability_node"
            
        }
    )

    workflow.add_conditional_edges(
        "reschedule_guard",
        check_active_booking_router,
        {
            "no_booking": "no_booking_response",
            "reschedule": "reschedule_booking"
        }
    )


    workflow.add_edge("reschedule_booking", "reschedule_validation")

    workflow.add_conditional_edges(
        "reschedule_validation",
        reschedule_validation_router,
        {
            "reschedule_followup": "reschedule_followup",
            "reschedule_availability": "reschedule_availability"
        }
    )

    workflow.add_edge("knowledge_base", END)
    workflow.add_edge("emergency_escalation", END)
    workflow.add_edge("refusal_node", END)
    workflow.add_edge("cancel_booking", END)
    workflow.add_edge("show_booking", END)
    workflow.add_edge("availability_node", END)
    workflow.add_edge("booking_followup", END)
    workflow.add_edge("reschedule_followup", END)
    workflow.add_edge("reschedule_availability", END)
    workflow.add_edge("no_booking_response", END)

    app= workflow.compile(checkpointer= memory)

    return app

