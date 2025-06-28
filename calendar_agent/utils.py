import re
import dateparser
from datetime import datetime, timedelta
import pytz

def get_user_intent(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ["book", "schedule", "appointment", "meeting", "reserve"]):
        return "book"
    if any(word in text for word in ["free", "available", "availability", "open"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    """Improved slot extraction that handles natural language like 'I want to book 2 July at 2 PM'"""
    user_tz = pytz.timezone(timezone)
    original_text = text.strip()
    text_lower = original_text.lower()

    # Map vague terms to times
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
            original_text = re.sub(term, tm, original_text, flags=re.IGNORECASE)
            break

    # Ensure there's a time if only a date is mentioned
    if not any(marker in text_lower for marker in ["am", "pm", ":", "hour", "minute"]):
        if any(day in text_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]) or "july" in text_lower or "august" in text_lower:
            original_text += " 10:00 AM"

    # Try parsing directly with fallback to RELATIVE_BASE
    parsed = dateparser.parse(
        original_text,
        settings={
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime.now(user_tz)
        }
    )

    if not parsed:
        print(f"[ERROR] Failed to parse: '{original_text}'")
        return None

    # Default duration logic
    duration = 30
    if "hour" in text_lower:
        hour_match = re.search(r'(\d+)\s*hour', text_lower)
        duration = 60 * int(hour_match.group(1)) if hour_match else 60
    minutes_match = re.search(r"(\d+)\s*minute", text_lower)
    if minutes_match:
        duration = int(minutes_match.group(1))

    # Final formatting
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
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        return 9 <= start_dt.hour < 18
    except:
        return True

def suggest_alternative(slots: dict) -> str:
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        business_start = 9
        business_end = 18

        if start_dt.hour < business_start or start_dt.hour >= business_end:
            next_day = start_dt + timedelta(days=1)
            return f"{next_day.strftime('%A')} morning or afternoon"

        alt1 = start_dt + timedelta(hours=1)
        alt2 = start_dt + timedelta(hours=2)
        return f"{alt1.strftime('%I:%M %p')} or {alt2.strftime('%I:%M %p')}"
    except Exception:
        return "tomorrow morning or afternoon"

def _format_time_friendly(datetime_str: str) -> str:
    try:
        dt = datetime.fromisoformat(datetime_str)
        now = datetime.now()
        if dt.date() == now.date():
            return f"today at {dt.strftime('%I:%M %p')}"
        elif dt.date() == now.date() + timedelta(days=1):
            return f"tomorrow at {dt.strftime('%I:%M %p')}"
        return dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        return datetime_str