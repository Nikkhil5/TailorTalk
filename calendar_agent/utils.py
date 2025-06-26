import re
import dateparser
from datetime import datetime, timedelta
import pytz

def get_user_intent(text: str) -> str:
    """Recognize user intent from text."""
    text = text.lower()
    if any(word in text for word in ["book", "schedule", "appointment", "meeting"]):
        return "book"
    if any(word in text for word in ["free", "available", "availability"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    """
    Extract time/date slots with business-hour defaults.
    Ensures day-only queries default to 10:00 AM.
    """
    user_tz = pytz.timezone(timezone)
    text_lower = text.lower()

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
        if term in text_lower:
            text = re.sub(term, tm, text, flags=re.IGNORECASE)
            break

    # Force business hours for day-only queries
    if not any(marker in text_lower for marker in ["am", "pm", ":", "hour", "minute"]):
        if "today" in text_lower or "tomorrow" in text_lower or \
           any(day in text_lower for day in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]):
            text += " 10:00 AM"

    # Parse with dateparser
    parsed = dateparser.parse(
        text,
        settings={
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future"
        }
    )
    if not parsed:
        return None

    # Determine meeting duration
    duration = 30
    if "hour" in text_lower:
        duration = 60
    minutes_match = re.search(r"(\d+)\s*minute", text_lower)
    if minutes_match:
        duration = int(minutes_match.group(1))

    # Build slot dict
    start = parsed.astimezone(user_tz)
    end = start + timedelta(minutes=duration)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": timezone
    }

def suggest_alternative(slots: dict) -> str:
    """
    Suggest business-appropriate alternative times.
    Never suggests times before 9 AM or after 6 PM.
    """
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        business_start = 9  # 9 AM
        business_end = 18   # 6 PM

        # Handle midnight and non-business hours
        if start_dt.hour < business_start or start_dt.hour >= business_end:
            next_day = start_dt + timedelta(days=1)
            opt1 = next_day.replace(hour=10, minute=0)  # 10 AM
            opt2 = next_day.replace(hour=14, minute=0)  # 2 PM
            return f"{opt1.strftime('%A at %I:%M %p')} or {opt2.strftime('%I:%M %p')}"

        # Within business hours - suggest +1h and +2h
        alt1_hour = min(start_dt.hour + 1, business_end - 1)
        alt2_hour = min(start_dt.hour + 2, business_end - 1)
        alt1 = start_dt.replace(hour=alt1_hour, minute=0)
        alt2 = start_dt.replace(hour=alt2_hour, minute=0)
        
        return f"{alt1.strftime('%I:%M %p')} or {alt2.strftime('%I:%M %p')}"
    except Exception:
        return "10:00 AM or 2:00 PM tomorrow"

def _format_time_friendly(datetime_str: str) -> str:
    """Convert ISO datetime to user-friendly format."""
    try:
        dt = datetime.fromisoformat(datetime_str)
        return dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        return datetime_str