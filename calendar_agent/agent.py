from typing import TypedDict
from langgraph.graph import StateGraph, END
from gcal import check_availability, book_appointment
from utils import (
    get_user_intent,
    extract_slots,
    suggest_alternative,
    
)
from utils import _format_time_friendly


class AgentState(TypedDict):
    user_input: str
    intent: str
    slots: dict
    response: str
    completed: bool
    context: dict
    waiting_for: str

def recognize_intent(state: AgentState) -> AgentState:
    """Determine user intent with context awareness."""
    if state.get("completed"):
        return state

    if state.get("waiting_for") == "time_range":
        state["intent"] = "check_availability"
    elif state.get("waiting_for") == "booking_time":
        state["intent"] = "book"
    elif state.get("waiting_for") == "confirmation":
        state["intent"] = "book"
    else:
        state["intent"] = get_user_intent(state["user_input"])
    return state

def handle_booking(state: AgentState) -> AgentState:
    """Main booking handler with confirmation flow."""
    if state.get("completed"):
        return state

    state.setdefault("context", {})

    # Handle confirmation responses
    if state.get("waiting_for") == "confirmation":
        if state["user_input"].strip().lower() in ["yes", "y"]:
            book_appointment(state["context"]["pending_booking"])
            booked_time = _format_time_friendly(state["context"]["pending_booking"]["start"])
            state["response"] = f"Booked! Your meeting is scheduled for {booked_time}."
        else:
            state["response"] = "Booking canceled. What time would you prefer?"
        _reset_state(state)
        return state

    try:
        if state["intent"] == "check_availability":
            return _handle_availability(state)
        if state["intent"] == "book":
            return _handle_booking_request(state)
        state["response"] = "I can help book appointments or check availability. What would you like to do?"
        state["completed"] = True
    except Exception as e:
        state["response"] = f"Error: {str(e)}"
        state["completed"] = True

    return state

def _handle_availability(state: AgentState) -> AgentState:
    """Availability check with business-hour defaults."""
    if state.get("waiting_for") == "time_range":
        combined_input = f"{state['context'].get('date', '')} {state['user_input']}"
        slots = extract_slots(combined_input)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and any(day in state["user_input"].lower() for day in [
            "monday","tuesday","wednesday","thursday","friday","saturday","sunday"
        ]):
            state["context"]["date"] = state["user_input"]
            state["waiting_for"] = "time_range"
            state["response"] = "What time? (e.g., 'morning', 'afternoon' or '2 PM')"
            return state

    if not slots:
        state["response"] = "Please specify a date and time (e.g., 'Friday 2 PM')."
        return state

    if check_availability(slots):
        # Store slot and ask for confirmation
        state["context"]["pending_booking"] = slots
        state["waiting_for"] = "confirmation"
        friendly = _format_time_friendly(slots["start"])
        state["response"] = f"You're free on {friendly}. Book it? (yes/no)"
    else:
        # Suggest business-hour alternatives
        alt = suggest_alternative(slots)
        state["waiting_for"] = "time_range"
        state["response"] = f"Unavailable. Try: {alt}"
        state["completed"] = False  # Stay in conversation

    return state

def _handle_booking_request(state: AgentState) -> AgentState:
    """Booking handler with confirmation."""
    if state.get("waiting_for") == "booking_time":
        combined_input = f"{state['context'].get('booking_request', '')} {state['user_input']}"
        slots = extract_slots(combined_input)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and any(w in state["user_input"].lower() for w in ["book","schedule"]):
            state["context"]["booking_request"] = state["user_input"]
            state["waiting_for"] = "booking_time"
            state["response"] = "When? (e.g., 'Tomorrow 3PM')"
            return state

    if not slots:
        state["response"] = "Please specify a date and time (e.g., 'Friday 3PM')."
        return state

    if check_availability(slots):
        # Store slot and confirm
        state["context"]["pending_booking"] = slots
        state["waiting_for"] = "confirmation"
        friendly = _format_time_friendly(slots["start"])
        state["response"] = f"Available at {friendly}. Book it? (yes/no)"
    else:
        alt = suggest_alternative(slots)
        state["waiting_for"] = "booking_time"
        state["response"] = f"Unavailable. Try: {alt}"
        state["completed"] = False  # Stay in conversation

    return state

def _reset_state(state: AgentState) -> None:
    """Reset conversation state after completion."""
    state["completed"] = True
    state["waiting_for"] = ""
    state["context"] = {}

# Build LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("recognize_intent_node", recognize_intent)
workflow.add_node("handle_booking_node", handle_booking)
workflow.set_entry_point("recognize_intent_node")
workflow.add_edge("recognize_intent_node", "handle_booking_node")
workflow.add_edge("handle_booking_node", END)
graph = workflow.compile()

def run_agent(user_input: str, state: dict) -> dict:
    """Run agent workflow with state preservation."""
    if not state:
        state = {
            "user_input": user_input,
            "intent": "",
            "slots": {},
            "response": "",
            "completed": False,
            "context": {},
            "waiting_for": ""
        }
    else:
        state["user_input"] = user_input
        if not state.get("waiting_for"):
            state["completed"] = False

    updated_state = graph.invoke(state)
    return {
        "response": updated_state["response"],
        "state": updated_state
    }
