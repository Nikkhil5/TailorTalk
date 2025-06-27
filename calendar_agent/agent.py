from typing import TypedDict
from langgraph.graph import StateGraph, END
from gcal import check_availability, book_appointment
from utils import (
    get_user_intent,
    extract_slots,
    suggest_alternative,
    _format_time_friendly,
    is_business_hours
)
import re
import datetime

class AgentState(TypedDict):
    user_input: str
    intent: str
    slots: dict
    response: str
    completed: bool
    context: dict
    waiting_for: str
    last_booked: dict
    conversation_history: list

def recognize_intent(state: AgentState) -> AgentState:
    """Advanced intent recognition with context awareness"""
    if state.get("completed"):
        return state
        
    # Use conversation history to understand context
    conversation_context = " ".join(state.get("conversation_history", []))
    full_context = f"{conversation_context} {state['user_input']}".lower()
    
    # Check for time references relative to previous bookings
    if "same time" in full_context and state.get("last_booked"):
        state["context"]["reference_slot"] = state["last_booked"]
        state["intent"] = "book"
        return state
        
    # Check for explicit intents
    if re.search(r'\b(book|schedule|appointment|meeting)\b', full_context):
        state["intent"] = "book"
    elif re.search(r'\b(free|available|availability|open)\b', full_context):
        state["intent"] = "check_availability"
    else:
        # Check for implicit time-based requests
        if any(word in full_context for word in ["tomorrow", "monday", "tuesday", "wednesday", 
                                               "thursday", "friday", "saturday", "sunday"]):
            state["intent"] = "check_availability"
        else:
            state["intent"] = get_user_intent(state["user_input"])
    
    return state

def handle_booking(state: AgentState) -> AgentState:
    """Main handler with intelligent context switching"""
    state.setdefault("context", {})
    state.setdefault("conversation_history", [])
    
    # Add current input to history
    state["conversation_history"].append(state["user_input"])
    
    # Handle conversation resets
    if re.search(r'\b(start over|reset|begin again)\b', state["user_input"].lower()):
        _reset_state(state)
        state["response"] = "Okay, let's start fresh. How can I help?"
        return state
    
    # Handle cancellations
    if re.search(r'\b(cancel|stop|never mind)\b', state["user_input"].lower()):
        _reset_state(state)
        state["response"] = "Booking canceled. What would you like to do next?"
        return state
        
    try:
        # Handle follow-up responses
        if state.get("waiting_for") == "confirmation":
            return _handle_confirmation(state)
        if state.get("waiting_for") == "time_range":
            return _handle_time_range(state)
            
        # Process primary intents
        if state["intent"] == "check_availability":
            return _handle_availability(state)
        if state["intent"] == "book":
            return _handle_booking_request(state)
            
        return _handle_unknown_intent(state)
        
    except Exception as e:
        return _handle_error(state, e)

def _handle_confirmation(state: AgentState) -> AgentState:
    """Process booking confirmations intelligently"""
    user_input = state["user_input"].strip().lower()
    
    if user_input in ["yes", "y", "yeah", "sure", "ok", "confirm"]:
        # Book appointment
        if book_appointment(state["context"]["pending_booking"]):
            booked_time = _format_time_friendly(state["context"]["pending_booking"]["start"])
            state["response"] = f"✅ Booked! Your meeting is scheduled for {booked_time}."
            state["last_booked"] = state["context"]["pending_booking"]
            _reset_state(state)
        else:
            state["response"] = "⚠️ Booking failed. Please try a different time."
            state["waiting_for"] = "time_range"
        
    elif user_input in ["no", "n", "nope", "cancel"]:
        state["response"] = "Okay, let's try another time. What would you prefer?"
        state["waiting_for"] = "time_range"
        
    else:
        # Handle ambiguous responses
        state["response"] = "Please confirm with 'yes' or 'no'. " + state["context"].get("confirmation_prompt", "")
        
    return state

def _handle_time_range(state: AgentState) -> AgentState:
    """Process time inputs with smart retry logic"""
    # Handle "same time" references
    if "same time" in state["user_input"].lower() and state.get("last_booked"):
        slots = state["last_booked"].copy()
        # Adjust date to new reference
        if "tomorrow" in state["user_input"].lower():
            new_date = datetime.datetime.now() + datetime.timedelta(days=1)
            slots["start"] = slots["start"].replace(day=new_date.day, month=new_date.month, year=new_date.year)
        return _process_slots(state, slots)
    
    combined_input = f"{state['context'].get('date', '')} {state['user_input']}"
    slots = extract_slots(combined_input)
    
    if not slots:
        # Provide specific guidance for failed parsing
        state["response"] = (
            "I couldn't understand that time. Please try:\n"
            "- 'Tomorrow 3 PM'\n"
            "- 'Friday morning'\n"
            "- 'Next week at 2:30 PM'"
        )
        return state
        
    return _process_slots(state, slots)

def _handle_availability(state: AgentState) -> AgentState:
    """Availability check with intelligent defaults"""
    # Handle relative time references
    if "tomorrow" in state["user_input"].lower() and not re.search(r'\d', state["user_input"]):
        state["context"]["date"] = "tomorrow"
        state["waiting_for"] = "time_range"
        state["response"] = "What time tomorrow? (e.g., 'tomorrow morning at 10:00 AM', 'tomorrow afternoon at 2:00 PM' or 'tomorrow evening at 7:00 PM')"
        return state
        
    slots = extract_slots(state["user_input"])
    return _process_slots(state, slots) if slots else _request_better_input(state)

def _handle_booking_request(state: AgentState) -> AgentState:
    """Booking handler with context-aware slot extraction"""
    # Handle "book" with relative references
    if "same time" in state["user_input"].lower() and state.get("last_booked"):
        return _process_slots(state, state["last_booked"].copy())
        
    slots = extract_slots(state["user_input"])
    return _process_slots(state, slots) if slots else _request_better_input(state)

def _process_slots(state: AgentState, slots: dict) -> AgentState:
    """Central slot processing with intelligent responses"""
    # Check business hours
    if not is_business_hours(slots):
        alt = suggest_alternative(slots)
        state["response"] = f"⏰ That time is outside business hours. How about {alt}?"
        state["waiting_for"] = "time_range"
        return state
        
    if check_availability(slots):
        state["context"]["pending_booking"] = slots
        state["waiting_for"] = "confirmation"
        friendly = _format_time_friendly(slots["start"])
        state["response"] = f"You're free on {friendly}. Book it? (yes/no)"
        state["context"]["confirmation_prompt"] = state["response"]
    else:
        alt = suggest_alternative(slots)
        state["waiting_for"] = "time_range"
        state["response"] = f"⏰ Unavailable at that time. How about {alt}?"
    
    return state

def _request_better_input(state: AgentState) -> AgentState:
    """Intelligent input guidance based on conversation context"""
    if any(word in state["user_input"].lower() for word in ["time", "hour", "minute"]):
        state["response"] = "Please include a specific time (e.g., '2 PM' or 'morning')."
    elif any(word in state["user_input"].lower() for word in ["date", "day", "tomorrow"]):
        state["response"] = "Please include a specific date (e.g., 'Friday' or 'July 5th')."
    else:
        state["response"] = (
            "Please include both date AND time in your request.\n\n"
            "**Examples**:\n"
            "- 'Friday 2 PM'\n"
            "- 'Tomorrow morning'\n"
            "- 'Next week Tuesday at 3 PM'"
        )
    
    return state

def _handle_unknown_intent(state: AgentState) -> AgentState:
    """Context-aware response for unknown intents"""
    if "book" in state["conversation_history"][-1].lower() if state["conversation_history"] else "":
        state["response"] = "When would you like to book? (e.g., 'Tomorrow 3PM')"
        state["waiting_for"] = "time_range"
    elif "available" in state["conversation_history"][-1].lower() if state["conversation_history"] else "":
        state["response"] = "When should I check? (e.g., 'Friday afternoon')"
        state["waiting_for"] = "time_range"
    else:
        state["response"] = (
            "I can help with:\n"
            "🔹 Booking appointments\n"
            "🔹 Checking availability\n\n"
            "**Try something like**:\n"
            "- 'Book a meeting tomorrow at 2 PM'\n"
            "- 'What's free next week?'\n"
            "- 'Check my Friday availability'"
        )
    
    state["completed"] = True
    return state

def _handle_error(state: AgentState, error: Exception) -> AgentState:
    """Graceful error recovery"""
    state["response"] = (
        "⚠️ I encountered an issue: " + str(error) + "\n\n"
        "Let's try again! Please rephrase your request."
    )
    _reset_state(state)
    return state

def _reset_state(state: AgentState) -> None:
    """Complete state reset"""
    state.update({
        "completed": True,
        "waiting_for": "",
        "context": {}
    })

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("recognize_intent_node", recognize_intent)
workflow.add_node("handle_booking_node", handle_booking)
workflow.set_entry_point("recognize_intent_node")
workflow.add_edge("recognize_intent_node", "handle_booking_node")
workflow.add_edge("handle_booking_node", END)
graph = workflow.compile()

def run_agent(user_input: str, state: dict) -> dict:
    """Stateful agent execution with conversation tracking"""
    if not state or state.get("completed"):
        state = {
            "user_input": user_input,
            "intent": "",
            "slots": {},
            "response": "",
            "completed": False,
            "context": {},
            "waiting_for": "",
            "last_booked": None,
            "conversation_history": []
        }
    else:
        state["user_input"] = user_input
        state["completed"] = False

    updated_state = graph.invoke(state)
    return {
        "response": updated_state["response"],
        "state": updated_state
    }