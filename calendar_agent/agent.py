from typing import TypedDict
from langgraph.graph import StateGraph, END
from gcal import check_availability, book_appointment
from utils import get_user_intent, extract_slots, suggest_alternative

class AgentState(TypedDict):
    user_input: str
    intent: str
    slots: dict
    response: str
    completed: bool
    context: dict
    waiting_for: str

def recognize_intent(state: AgentState) -> AgentState:
    """Determine user intent with conversation context"""
    if state.get("completed"):
        return state
    
    # Handle follow-up responses
    if state.get("waiting_for") == "time_range":
        state["intent"] = "check_availability"
    elif state.get("waiting_for") == "booking_time":
        state["intent"] = "book"
    else:
        state["intent"] = get_user_intent(state["user_input"])
    
    return state

def handle_booking(state: AgentState) -> AgentState:
    """Process booking/availability requests with context"""
    if state.get("completed"):
        return state
    
    # Initialize empty context if needed
    state.setdefault("context", {})
    
    try:
        if state["intent"] == "check_availability":
            return _handle_availability(state)
        elif state["intent"] == "book":
            return _handle_booking_request(state)
        else:
            state["response"] = "I can help book appointments or check availability. What would you like to do?"
            state["completed"] = True
    except Exception as e:
        state["response"] = f"Error processing request: {str(e)}"
        state["completed"] = True
    
    return state

def _handle_availability(state: AgentState) -> AgentState:
    """Process availability check requests"""
    if state.get("waiting_for") == "time_range":
        combined_input = f"{state['context'].get('date', '')} {state['user_input']}"
        slots = extract_slots(combined_input)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and any(day in state["user_input"].lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            state["context"]["date"] = state["user_input"]
            state["waiting_for"] = "time_range"
            state["response"] = "Please specify a time range (e.g. '2-4 PM')"
            return state
    
    if not slots:
        state["response"] = "Please specify a date and time (e.g. 'Friday 2-4 PM')"
        return state
    
    if check_availability(slots):
        state["response"] = f"You're free from {slots['start']} to {slots['end']}"
    else:
        state["response"] = f"Busy during that time. Try: {suggest_alternative(slots)}"
    
    _reset_state(state)
    return state

def _handle_booking_request(state: AgentState) -> AgentState:
    """Process booking requests"""
    if state.get("waiting_for") == "booking_time":
        combined_input = f"{state['context'].get('booking_request', '')} {state['user_input']}"
        slots = extract_slots(combined_input)
    else:
        slots = extract_slots(state["user_input"])
        if not slots and ("book" in state["user_input"].lower() or "schedule" in state["user_input"].lower()):
            state["context"]["booking_request"] = state["user_input"]
            state["waiting_for"] = "booking_time"
            state["response"] = "When would you like to book? (e.g. 'Tomorrow 3PM')"
            return state
    
    if not slots:
        state["response"] = "Please specify a date and time (e.g. 'Friday 3PM')"
        return state
    
    if check_availability(slots):
        book_appointment(slots)
        state["response"] = f"Booked! Your meeting is scheduled for {slots['start']}"
    else:
        state["response"] = f"Unavailable. Try: {suggest_alternative(slots)}"
    
    _reset_state(state)
    return state

def _reset_state(state: AgentState) -> None:
    """Clean up conversation state after completion"""
    state["completed"] = True
    state["waiting_for"] = ""
    state["context"] = {}

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("recognize_intent_node", recognize_intent)
workflow.add_node("handle_booking_node", handle_booking)
workflow.set_entry_point("recognize_intent_node")
workflow.add_edge("recognize_intent_node", "handle_booking_node")
workflow.add_edge("handle_booking_node", END)
graph = workflow.compile()

def run_agent(user_input: str, state: dict) -> dict:
    """Execute agent workflow with conversation context"""
    # Initialize state if empty
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
        # Prepare for new processing
        state["user_input"] = user_input
        state["completed"] = False
    
    # Execute workflow
    updated_state = graph.invoke(state)
    return {
        "response": updated_state["response"],
        "state": updated_state
    }
