from typing import TypedDict
from langgraph.graph import StateGraph, END
from gcal import check_availability, book_appointment
from utils import (
    get_user_intent,
    extract_slots,
    suggest_alternative,
    _format_time_friendly
)
print("Loading calendar agent...")
class AgentState(TypedDict):
    user_input: str
    intent: str
    slots: dict
    response: str
    completed: bool
    context: dict
    waiting_for: str

def recognize_intent(state: AgentState) -> AgentState:
    """Determine user intent, respecting multi-turn context."""
    if state.get("completed"):
        return state

    if state.get("waiting_for") == "time_range":
        state["intent"] = "check_availability"
    elif state.get("waiting_for") == "booking_time":
        state["intent"] = "book"
    elif state.get("waiting_for") == "confirmation":
        state["intent"] = "book"  # Treat confirmation as booking intent
    else:
        state["intent"] = get_user_intent(state["user_input"])
    return state

def handle_booking(state: AgentState) -> AgentState:
    """Route to availability or booking handlers based on intent."""
    if state.get("completed"):
        return state

    state.setdefault("context", {})

    # Handle confirmation responses first
    if state.get("waiting_for") == "confirmation":
        if state["user_input"].strip().lower() in ["yes", "y"]:
            # Book the pending appointment
            book_appointment(state["context"]["pending_booking"])
            friendly = _format_time_friendly(state["context"]["pending_booking"]["start"])
            state["response"] = f"Your meeting has been booked for {friendly}."
        else:
            state["response"] = "Okay, let me know another time you'd like."
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
        state["response"] = f"Error processing request: {e}"
        state["completed"] = True

    return state

def _handle_availability(state: AgentState) -> AgentState:
    """Process availability checks with guided prompts."""
    if state.get("waiting_for") == "time_range":
        combo = f"{state['context'].get('date', '')} {state['user_input']}"
        slots = extract_slots(combo)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and any(day in state["user_input"].lower() for day in [
            "monday","tuesday","wednesday","thursday","friday","saturday","sunday"
        ]):
            state["context"]["date"] = state["user_input"]
            state["waiting_for"] = "time_range"
            state["response"] = "What time would you prefer? (e.g., 'morning', 'afternoon' or '2 PM')"
            return state

    if not slots:
        state["response"] = "Please specify a date and time (e.g., 'Friday morning' or 'Friday 2 PM')."
        return state

    if check_availability(slots):
        friendly = _format_time_friendly(slots["start"])
        # Store slot and ask for confirmation
        state["context"]["pending_booking"] = slots
        state["waiting_for"] = "confirmation"
        state["response"] = f"You're free on {friendly}. Would you like to book this slot? (yes/no)"
    else:
        alt = suggest_alternative(slots)
        # Stay in time_range context for follow-up
        state["waiting_for"] = "time_range"
        state["response"] = f"That time is unavailable. How about {alt}?"
        # Keep context for next input
        state["completed"] = False

    return state

def _handle_booking_request(state: AgentState) -> AgentState:
    """Process booking requests, asking for time if needed."""
    if state.get("waiting_for") == "booking_time":
        combo = f"{state['context'].get('booking_request', '')} {state['user_input']}"
        slots = extract_slots(combo)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and any(w in state["user_input"].lower() for w in ["book","schedule"]):
            state["context"]["booking_request"] = state["user_input"]
            state["waiting_for"] = "booking_time"
            state["response"] = "When would you like to book? (e.g., 'Tomorrow 3PM')"
            return state

    if not slots:
        state["response"] = "Please specify a date and time (e.g., 'Friday 3PM')."
        return state

    if check_availability(slots):
        # Store slot and ask for confirmation
        state["context"]["pending_booking"] = slots
        state["waiting_for"] = "confirmation"
        friendly = _format_time_friendly(slots["start"])
        state["response"] = f"The slot at {friendly} is available. Shall I book it? (yes/no)"
    else:
        alt = suggest_alternative(slots)
        # Stay in booking_time context for follow-up
        state["waiting_for"] = "booking_time"
        state["response"] = f"That time is unavailable. Try: {alt}"
        state["completed"] = False

    return state

def _reset_state(state: AgentState) -> None:
    """Clean up state after a completed turn."""
    state["completed"] = True
    state["waiting_for"] = ""
    state["context"] = {}

# Build the LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("recognize_intent_node", recognize_intent)
workflow.add_node("handle_booking_node", handle_booking)
workflow.set_entry_point("recognize_intent_node")
workflow.add_edge("recognize_intent_node", "handle_booking_node")
workflow.add_edge("handle_booking_node", END)
graph = workflow.compile()

def run_agent(user_input: str, state: dict) -> dict:
    """Invoke the workflow with the current user input and state."""
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
        # Only reset user input, keep context
        state["user_input"] = user_input
        # Only mark as not completed if we're not in a waiting state
        if not state.get("waiting_for"):
            state["completed"] = False

    updated = graph.invoke(state)
    return {
        "response": updated["response"],
        "state": updated
    }
