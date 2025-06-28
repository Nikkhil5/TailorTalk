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
    user_tz = pytz.timezone(timezone)
    original_text = text
    text_lower = text.lower().strip()

    # Step 1: Clean text while preserving structure
    clean_text = re.sub(
        r'\b(?:yes|please|book|schedule|appointment|meeting|call|wanna|want to|can you|for)\b',
        '', text_lower, flags=re.IGNORECASE
    )
    clean_text = clean_text.strip()
    clean_text = re.sub(r'\b(at|on|by)\b', ' ', clean_text)  # Remove unnecessary prepositions
    clean_text = re.sub(r'\s+', ' ', clean_text)

    # Step 2: Add fallback for month/day-only inputs (like "15 July")
    month_day_match = re.search(r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b', clean_text)
    if month_day_match and "next" in clean_text:
        next_month = datetime.now(user_tz).month + 1
        current_year = datetime.now(user_tz).year
        if next_month > 12:
            next_month = 1
            current_year += 1
        clean_text += f" {current_year}"

    # Step 3: Map vague terms to specific times
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

    # Step 4: Handle ambiguous inputs
    # Add default time if only date is mentioned
    if not any(t in clean_text for t in ["am", "pm", ":", "hour", "minute"]):
        clean_text = clean_text.strip() + " at 10:00 AM"


    # Step 5: Multiple parse attempts
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

    # Step 6: Duration
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