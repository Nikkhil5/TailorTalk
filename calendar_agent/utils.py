import dateparser
from datetime import datetime, timedelta
import pytz

def get_user_intent(text: str) -> str:
    text = text.lower()
    print(text)
    if any(word in text for word in ["book", "schedule", "appointment", "meeting"]):
        return "book"
    elif any(word in text for word in ["free", "available", "availability"]):
        return "check_availability"
    return "unknown"

def extract_slots(text: str, timezone: str = "Asia/Kolkata") -> dict:
    from datetime import timedelta
    import dateparser
    import pytz
    import re

    user_tz = pytz.timezone(timezone)
    text_lower = text.lower()

    # Map vague phrases to actual time
    vague_map = {
        "morning": "9:00 AM",
        "afternoon": "2:00 PM",
        "evening": "6:00 PM",
        "night": "9:00 PM",
        "noon": "12:00 PM",
        "midnight": "12:00 AM"
    }

    # Replace vague word with actual time
    for vague, concrete in vague_map.items():
        if vague in text_lower:
            print(f"[DEBUG] Replacing '{vague}' with '{concrete}'")
            text = re.sub(vague, concrete, text_lower)
            break

    
    match = re.search(r"(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}(:\d{2})?\s*(am|pm)?)", text, re.IGNORECASE)
    if match:
        text = text[match.start():]
    else:
        print("DEBUG..... Could not isolate date/time phrase")
    
    print("DEBUG Final text for parsing ....", text)

    parsed = dateparser.parse(
        text,
        settings={
            'TIMEZONE': timezone,
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future'
        }
    )

    print("[DEBUG] Parsed datetime:", parsed)

    if not parsed:
        return None

    duration = 30
    if "hour" in text_lower:
        duration = 60
    elif "minute" in text_lower:
        try:
            duration = int(text_lower.split("minute")[0].split()[-1])
        except:
            pass

    start = parsed.astimezone(user_tz)
    end = start + timedelta(minutes=duration)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": timezone
    }
  

def suggest_alternative(slots: dict) -> str:
    from datetime import datetime, timedelta
    try:
        start = datetime.fromisoformat(slots["start"])
        return f"{start + timedelta(hours=1)} or {start + timedelta(hours=2)}"
    except:
        return "tomorrow at the same time or an hour later"
