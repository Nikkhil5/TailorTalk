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
    user_tz = pytz.timezone(timezone)
    original_text = text
    text_lower = text.lower().strip()

    clean_text = re.sub(
        r'\b(?:yes|please|book|schedule|appointment|meeting|call|wanna|want to|can you|for)\b',
        '', text_lower, flags=re.IGNORECASE
    ).strip()

    clean_text = re.sub(r'\b(at|on|by)\b', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)

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

    clean_text = re.sub(r'(\d+)([ap]m)', r'\1 \2', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'(\d{1,2})[:]?(\d{2})', r'\1:\2', clean_text)

    if not any(word in clean_text for word in ["mon","tue","wed","thu","fri","sat","sun","today","tomorrow","week","month"]):
        if re.search(r'\d{1,2}:\d{2}\s*(am|pm)', clean_text, re.IGNORECASE):
            clean_text = "today " + clean_text
    elif not any(marker in clean_text for marker in ["am", "pm", ":", "hour", "minute"]):
        clean_text += " 10:00 AM"

    parsed = None
    parse_attempts = [
        clean_text,
        f"{clean_text} {datetime.now().year}",
        original_text
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

    duration = 30
    if "hour" in clean_text:
        hour_match = re.search(r'(\d+)\s*hour', clean_text)
        duration = 60 * int(hour_match.group(1)) if hour_match else 60
    minutes_match = re.search(r"(\d+)\s*minute", clean_text)
    if minutes_match:
        duration = int(minutes_match.group(1))

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

def suggest_alternative(slots: dict, only_free=False) -> str:
    try:
        start_dt = datetime.fromisoformat(slots["start"])
        user_tz = start_dt.tzinfo or pytz.timezone("Asia/Kolkata")
        suggestions = []

        base_day = start_dt.replace(minute=0, second=0, microsecond=0)

        for hour in range(9, 18):
            alt_time = base_day.replace(hour=hour)
            alt_end = alt_time + timedelta(minutes=30)
            alt_slot = {
                "start": alt_time.isoformat(),
                "end": alt_end.isoformat(),
                "timezone": slots.get("timezone", "Asia/Kolkata")
            }
            if only_free and not check_availability(alt_slot):
                continue
            suggestions.append(alt_time.strftime("%I:%M %p"))
            if len(suggestions) == 2:
                break

        if suggestions:
            return f"{suggestions[0]} or {suggestions[1]}"
        return "10:00 AM or 2:00 PM tomorrow"

    except Exception as e:
        print("[suggest_alternative] error:", e)
        return "10:00 AM or 2:00 PM tomorrow"

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