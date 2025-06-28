import re
import dateparser
from datetime import datetime, timedelta
import pytz
from gcal import check_availability

def get_user_intent(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ["book", "schedule", "appointment", "meeting", "reserve"]):
        return "book"
    if any(word in text for word in ["free", "available", "availability", "open"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    """Robust slot extraction with enhanced parsing and error handling"""
    user_tz = pytz.timezone(timezone)
    original_text = text
    text_lower = text.lower().strip()

    # Step 1: Clean text while preserving critical structure
    clean_text = re.sub(
        r'\b(?:yes|please|book|schedule|appointment|meeting|call|wanna|want to|can you|for)\b', 
        '', text_lower, flags=re.IGNORECASE
    )
    clean_text = clean_text.strip()

    # Normalize 'next week Tuesday' → 'Tuesday next week'
    clean_text = re.sub(r'next week (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', 
                        r'\1 next week', clean_text, flags=re.IGNORECASE)

    # Preserve critical prepositions
    clean_text = re.sub(r'\b(at|on|by)\b', ' ', clean_text)  # Remove prepositions
    clean_text = re.sub(r'\s+', ' ', clean_text)  # Normalize spaces

    # Step 2: Map vague terms to specific times
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

    # Step 3: Handle time formats
    clean_text = re.sub(r'(\d+)([ap]m)', r'\1 \2', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'(\d{1,2})[:]?(\d{2})', r'\1:\2', clean_text)  # Normalize 2:30 -> 2:30

    # Step 4: Add context for ambiguous inputs
    if not any(word in clean_text for word in ["mon","tue","wed","thu","fri","sat","sun","today","tomorrow","week","month"]):
        if re.search(r'\d{1,2}:\d{2}\s*(am|pm)', clean_text, re.IGNORECASE):
            clean_text = "today " + clean_text
    elif not any(marker in clean_text for marker in ["am", "pm", ":", "hour", "minute"]):
        clean_text += " 10:00 AM"

    # Step 5: Multiple parse attempts
    parsed = None
    parse_attempts = [
        clean_text,
        f"{clean_text} {datetime.now().year}",  # Add year context
        original_text  # Fallback to original
    ]

    for attempt in parse_attempts:
        parsed = dateparser.parse(
            attempt,
            settings={
                "TIMEZONE": timezone,
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
                "PREFER_DAY_OF_MONTH": "first",
                "RELATIVE_BASE": datetime.now(pytz.timezone(timezone))
            }
        )
        if parsed:
            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)
            break

    if not parsed:
        print(f"[ERROR] Failed to parse: '{original_text}' → Attempts: {parse_attempts}")
        return None

    # Step 6: Duration handling
    duration = 30
    if "hour" in clean_text:
        hour_match = re.search(r'(\d+)\s*hour', clean_text)
        duration = 60 * int(hour_match.group(1)) if hour_match else 60
    minutes_match = re.search(r"(\d+)\s*minute", clean_text)
    if minutes_match:
        duration = int(minutes_match.group(1))

    # Step 7: Timezone handling
    if parsed.tzinfo is None:
        start = user_tz.localize(parsed)
    else:
        start = parsed.astimezone(user_tz)

    end = start + timedelta(minutes=duration)

    print(f"[SUCCESS] Parsed: '{original_text}' → {start.isoformat()}")

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
    """Suggest actual available alternatives by checking calendar."""
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        timezone = slots.get("timezone", "Asia/Kolkata")
        user_tz = pytz.timezone(timezone)
        suggestions = []

        for i in range(1, 5):  # Try next 4 half-hour blocks
            new_start = start_dt + timedelta(minutes=30 * i)
            new_end = new_start + timedelta(minutes=30)
            new_slot = {
                "start": new_start.isoformat(),
                "end": new_end.isoformat(),
                "timezone": timezone
            }
            if check_availability(new_slot):
                suggestions.append(new_start.strftime("%I:%M %p"))
            if len(suggestions) == 2:
                break

        if suggestions:
            return " or ".join(suggestions)
        else:
            return "tomorrow at 10:00 AM or 2:00 PM"
    except Exception as e:
        print("[suggest_alternative] error:", e)
        return "tomorrow at 10:00 AM or 2:00 PM"

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

# Test print
print(_format_time_friendly("2023-10-01T10:00:00+05:30"))
