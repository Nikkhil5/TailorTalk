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
    pending_date: str
    last_suggested_alternatives: list

def recognize_intent(state: AgentState) -> AgentState:
    if state.get("completed"):
        return state

    conversation_context = " ".join(state.get("conversation_history", []))
    full_context = f"{conversation_context} {state['user_input']}".lower()

    if "same time" in full_context and state.get("last_booked"):
        state["context"]["reference_slot"] = state["last_booked"]
        state["intent"] = "book"
        return state

    if re.search(r'\b(book|schedule|appointment|meeting)\b', full_context):
        state["intent"] = "book"
    elif re.search(r'\b(free|available|availability|open)\b', full_context):
        state["intent"] = "check_availability"
    else:
        if any(word in full_context for word in ["tomorrow", "monday", "tuesday", "wednesday",
                                                 "thursday", "friday", "saturday", "sunday"]):
            state["intent"] = "check_availability"
        else:
            state["intent"] = get_user_intent(state["user_input"])

    return state

def handle_booking(state: AgentState) -> AgentState:
    state.setdefault("context", {})
    state.setdefault("conversation_history", [])
    state["conversation_history"].append(state["user_input"])

    if re.search(r'\b(start over|reset|begin again)\b', state["user_input"].lower()):
        _reset_state(state)
        state["response"] = "Okay, let's start fresh. How can I help?"
        return state

    if re.search(r'\b(cancel|stop|never mind)\b', state["user_input"].lower()):
        _reset_state(state)
        state["response"] = "Booking canceled. What would you like to do next?"
        return state

    try:
        if state.get("waiting_for") == "confirmation":
            return _handle_confirmation(state)
        if state.get("waiting_for") == "time_range":
            return _handle_time_range(state)

        if state["intent"] == "check_availability":
            return _handle_availability(state)
        if state["intent"] == "book":
            return _handle_booking_request(state)

        return _handle_unknown_intent(state)

    except Exception as e:
        return _handle_error(state, e)

def _handle_confirmation(state: AgentState) -> AgentState:
    user_input = state["user_input"].strip().lower()

    if user_input in ["yes", "y", "yeah", "sure", "ok", "confirm"]:
        if book_appointment(state["context"]["pending_booking"]):
            booked_time = _format_time_friendly(state["context"]["pending_booking"]["start"])
            state["response"] = f"✅ Booked! Your meeting is scheduled for {booked_time}.\n\nWould you like to book something else?"
            state["last_booked"] = state["context"]["pending_booking"]
            _reset_state(state)
        else:
            state["response"] = "⚠️ Booking failed. Please try a different time."
            state["waiting_for"] = "time_range"
    elif user_input in ["no", "n", "nope", "cancel"]:
        state["response"] = "Okay, let's try another time. What would you prefer?"
        state["waiting_for"] = "time_range"
    else:
        possible_slots = extract_slots(state["user_input"])
        if possible_slots:
            state["waiting_for"] = "time_range"
            return _process_slots(state, possible_slots)

        state["response"] = (
            "Please confirm with 'yes' or 'no'.\n"
            "Or you can enter a new time (e.g., '2 July at 2 PM').\n\n"
            + state["context"].get("confirmation_prompt", "")
        )

    return state

def _handle_time_range(state: AgentState) -> AgentState:
    if state.get("last_suggested_alternatives"):
        user_input_clean = re.sub(r'[\s:-]', '', state["user_input"].lower())
        for alt in state["last_suggested_alternatives"]:
            alt_clean = re.sub(r'[\s:-]', '', alt.lower())
            if user_input_clean == alt_clean or user_input_clean in alt_clean:
                slots = extract_slots(alt)
                if slots:
                    return _process_slots(state, slots)

    if "same time" in state["user_input"].lower() and state.get("last_booked"):
        slots = state["last_booked"].copy()
        if "tomorrow" in state["user_input"].lower():
            new_date = datetime.datetime.now() + datetime.timedelta(days=1)
            slots["start"] = slots["start"].replace(day=new_date.day, month=new_date.month, year=new_date.year)
        return _process_slots(state, slots)

    combined_input = state["user_input"]
    if state.get("pending_date"):
        combined_input = f"{state['pending_date']} {state['user_input']}"
        state["pending_date"] = None

    slots = extract_slots(combined_input)

    if not slots:
        for msg in reversed(state.get("conversation_history", [])):
            if "next" in msg.lower() or "week" in msg.lower() or "friday" in msg.lower():
                retry_input = f"{msg} {state['user_input']}"
                slots = extract_slots(retry_input)
                if slots:
                    break

    if not slots:
        state["response"] = (
            "I couldn’t understand that time. Please try one of these:\n"
            "• 'Tomorrow at 2 PM'\n"
            "• 'Friday 11 AM'\n"
            "• 'Next week Tuesday at 3:30 PM'"
        )
        return state

    return _process_slots(state, slots)

def _handle_availability(state: AgentState) -> AgentState:
    if "tomorrow" in state["user_input"].lower() and not re.search(r'\d', state["user_input"]):
        state["context"]["date"] = "tomorrow"
        state["waiting_for"] = "time_range"
        state["response"] = "What time tomorrow? (e.g., 'morning', 'afternoon' or '2 PM')"
        return state

    slots = extract_slots(state["user_input"])
    return _process_slots(state, slots) if slots else _request_better_input(state)

def _handle_booking_request(state: AgentState) -> AgentState:
    if "same time" in state["user_input"].lower() and state.get("last_booked"):
        return _process_slots(state, state["last_booked"].copy())

    slots = extract_slots(state["user_input"])

    if not slots:
        prior_date = next((msg for msg in reversed(state["conversation_history"])
                          if any(d in msg.lower() for d in ["monday", "tuesday", "friday", "next week", "tomorrow"])), "")
        if prior_date:
            slots = extract_slots(f"{prior_date} {state['user_input']}")

    return _process_slots(state, slots) if slots else _request_better_input(state)

def _process_slots(state: AgentState, slots: dict) -> AgentState:
    print("[DEBUG] Booking slots:", slots)

    if not is_business_hours(slots):
        alt = suggest_alternative(slots)
        state["response"] = f"⏰ That time is outside business hours. How about {alt}?"
        state["waiting_for"] = "time_range"
        state["last_suggested_alternatives"] = [alt]
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
        state["last_suggested_alternatives"] = [alt]

    return state

def _request_better_input(state: AgentState) -> AgentState:
    state["response"] = (
        "I couldn’t understand the time clearly.\n\n**Try one of these:**\n"
        "• 'Tomorrow at 2 PM'\n"
        "• 'Friday 11 AM'\n"
        "• 'Next week Tuesday at 3:30 PM'"
    )
    return state

def _handle_unknown_intent(state: AgentState) -> AgentState:
    if state["conversation_history"] and "book" in state["conversation_history"][-1].lower():
        state["response"] = "When would you like to book? (e.g., 'Tomorrow 3PM')"
        state["waiting_for"] = "time_range"
    elif state["conversation_history"] and "available" in state["conversation_history"][-1].lower():
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
    state["response"] = (
        "⚠️ I encountered an issue: " + str(error) + "\n\n"
        "Let's try again! Please rephrase your request."
    )
    _reset_state(state)
    return state

def _reset_state(state: AgentState) -> None:
    state.update({
        "completed": True,
        "waiting_for": "",
        "context": {},
        "pending_date": None,
        "last_suggested_alternatives": []
    })

workflow = StateGraph(AgentState)
workflow.add_node("recognize_intent_node", recognize_intent)
workflow.add_node("handle_booking_node", handle_booking)
workflow.set_entry_point("recognize_intent_node")
workflow.add_edge("recognize_intent_node", "handle_booking_node")
workflow.add_edge("handle_booking_node", END)
graph = workflow.compile()

def run_agent(user_input: str, state: dict) -> dict:
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
            "conversation_history": [],
            "pending_date": None,
            "last_suggested_alternatives": []
        }
    else:
        state["user_input"] = user_input
        state["completed"] = False

    updated_state = graph.invoke(state)
    return {
        "response": updated_state["response"],
        "state": updated_state
    }
