import re
import dateparser
from datetime import datetime, timedelta
import pytz

def get_user_intent(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ["book", "schedule", "appointment", "meeting"]):
        return "book"
    if any(word in text for word in ["free", "available", "availability"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    """Robust slot extraction that handles conversational inputs"""
    user_tz = pytz.timezone(timezone)
    text_lower = text.lower().strip()
    
    # Remove common conversational phrases
    clean_text = re.sub(r'\b(?:yes|please|book|schedule|appointment|meeting|call|wanna|want to)\b', 
                        '', text_lower, flags=re.IGNORECASE)
    clean_text = clean_text.strip()
    
    print(f"[DEBUG] Cleaned text: '{clean_text}'")

    # Map vague terms to business hours
    time_map = {
        "morning": "10:00 AM",
        "afternoon": "2:00 PM",
        "evening": "5:00 PM",
        "night": "7:00 PM",
        "noon": "12:00 PM",
        "midnight": "12:00 AM"
    }
    for term, tm in time_map.items():
        if term in clean_text:
            clean_text = re.sub(term, tm, clean_text, flags=re.IGNORECASE)
            break

    # Handle time formats like "3PM" -> "3 PM"
    clean_text = re.sub(r'(\d+)([ap]m)', r'\1 \2', clean_text, flags=re.IGNORECASE)
    
    # Add default time if missing
    if not any(marker in clean_text for marker in ["am", "pm", ":", "hour", "minute"]):
        if any(day in clean_text for day in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]):
            clean_text += " 10:00 AM"

    print(f"[DEBUG] Final parsing text: '{clean_text}'")
    
    parsed = dateparser.parse(
        clean_text,
        settings={
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future"
        }
    )
    
    if not parsed:
        print(f"[ERROR] Failed to parse: '{clean_text}'")
        return None

    # Duration handling
    duration = 30
    if "hour" in clean_text:
        duration = 60
    minutes_match = re.search(r"(\d+)\s*minute", clean_text)
    if minutes_match:
        duration = int(minutes_match.group(1))

    # Timezone handling
    if parsed.tzinfo is None:
        start = user_tz.localize(parsed)
    else:
        start = parsed.astimezone(user_tz)
        
    end = start + timedelta(minutes=duration)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": timezone
    }
def suggest_alternative(slots: dict) -> str:
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        business_start = 9
        business_end = 18

        if start_dt.hour < business_start or start_dt.hour >= business_end:
            next_day = start_dt + timedelta(days=1)
            opt1 = next_day.replace(hour=10, minute=0)
            opt2 = next_day.replace(hour=14, minute=0)
            return f"{opt1.strftime('%A at %I:%M %p')} or {opt2.strftime('%I:%M %p')}"
        
        alt1_hour = min(start_dt.hour + 1, business_end - 1)
        alt2_hour = min(start_dt.hour + 2, business_end - 1)
        opt1 = start_dt.replace(hour=alt1_hour, minute=0)
        opt2 = start_dt.replace(hour=alt2_hour, minute=0)
        return f"{opt1.strftime('%I:%M %p')} or {opt2.strftime('%I:%M %p')}"
    except Exception as e:
        return "10:00 AM or 2:00 PM tomorrow"

def _format_time_friendly(datetime_str: str) -> str:
    try:
        dt = datetime.fromisoformat(datetime_str)
        return dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        return datetime_str
print(_format_time_friendly)