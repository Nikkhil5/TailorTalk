import re
import dateparser
from datetime import datetime, timedelta
import pytz

def get_user_intent(text: str) -> str:
    """Advanced intent recognition with context awareness"""
    text = text.lower()
    if any(word in text for word in ["book", "schedule", "appointment", "meeting", "reserve"]):
        return "book"
    if any(word in text for word in ["free", "available", "availability", "open"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    """Robust slot extraction with conversational context handling"""
    user_tz = pytz.timezone(timezone)
    text_lower = text.lower().strip()
    
    # Handle "same time" references
    if "same time" in text_lower:
        return None  # Let agent handle contextually
    
    # Remove conversational phrases while preserving time/date info
    clean_text = re.sub(
        r'\b(?:yes|please|book|schedule|appointment|meeting|call|wanna|want to|can you|for)\b', 
        '', text_lower, flags=re.IGNORECASE
    )
    clean_text = clean_text.strip()
    
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
    
    # Add default time if only date is specified
    if not any(marker in clean_text for marker in ["am", "pm", ":", "hour", "minute"]):
        if any(day in clean_text for day in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]):
            clean_text += " 10:00 AM"
        elif "today" in clean_text or "tomorrow" in clean_text:
            clean_text += " 10:00 AM"

    # Parse with enhanced settings
    parsed = dateparser.parse(
        clean_text,
        settings={
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "PREFER_DAY_OF_MONTH": "first",
            "RELATIVE_BASE": datetime.now(pytz.timezone(timezone))
        }
    )
    
    if not parsed:
        return None

    # Dynamic duration handling
    duration = 30
    if "hour" in clean_text:
        # Detect explicit hour count
        hour_match = re.search(r'(\d+)\s*hour', clean_text)
        duration = 60 * int(hour_match.group(1)) if hour_match else 60
    minutes_match = re.search(r"(\d+)\s*minute", clean_text)
    if minutes_match:
        duration = int(minutes_match.group(1))

    # Ensure timezone awareness
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

def is_business_hours(slots: dict) -> bool:
    """Check if time is within business hours (9AM-6PM)"""
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        return 9 <= start_dt.hour < 18
    except:
        return True  # Fail open if we can't determine

def suggest_alternative(slots: dict) -> str:
    """Suggest business-appropriate alternatives with context"""
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        
        # Handle business hours - suggest same day alternatives
        if is_business_hours(slots):
            alt1 = start_dt + timedelta(hours=1)
            alt2 = start_dt + timedelta(hours=2)
            return f"{alt1.strftime('%I:%M %p')} or {alt2.strftime('%I:%M %p')}"
        
        # Outside business hours - suggest next day business slots
        next_day = start_dt + timedelta(days=1)
        morning = next_day.replace(hour=10, minute=0)
        afternoon = next_day.replace(hour=14, minute=0)
        return f"{morning.strftime('%A at %I:%M %p')} or {afternoon.strftime('%I:%M %p')}"
        
    except Exception:
        return "10:00 AM or 2:00 PM tomorrow"

def _format_time_friendly(datetime_str: str) -> str:
    """User-friendly time formatting with natural language"""
    try:
        dt = datetime.fromisoformat(datetime_str)
        # Format for today/tomorrow detection
        now = datetime.now()
        if dt.date() == now.date():
            return f"today at {dt.strftime('%I:%M %p')}"
        elif dt.date() == now.date() + timedelta(days=1):
            return f"tomorrow at {dt.strftime('%I:%M %p')}"
        return dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        return datetime_str