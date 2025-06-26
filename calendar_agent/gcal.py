import streamlit as st
import base64
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_service_and_calendar_id():
    """
    Authenticate with Google Calendar API using credentials from Streamlit secrets.
    Returns:
        service: Google Calendar API service object
        calendar_id: The calendar ID to use for API calls
    """
    try:
        base64_creds = st.secrets["GOOGLE_CREDENTIALS_BASE64"]
        calendar_id = st.secrets["CALENDAR_ID"]
        json_str = base64.b64decode(base64_creds).decode('utf-8')
        service_account_info = json.loads(json_str)
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)
        return service, calendar_id
    except Exception as e:
        logger.error(f"Service authentication failed: {str(e)}")
        raise

def check_availability(slots: dict) -> bool:
    """
    Check availability using Google Calendar FreeBusy API.
    Args:
        slots: dict with 'start', 'end', and optionally 'timezone'
    Returns:
        True if the slot is free, False otherwise.
    """
    logger.info(f"Checking availability: {slots}")

    if not slots or 'start' not in slots or 'end' not in slots:
        logger.error("Invalid slots format")
        return False

    try:
        service, calendar_id = get_service_and_calendar_id()
        # Convert to UTC for Google Calendar API
        start_dt = datetime.fromisoformat(slots['start'])
        end_dt = datetime.fromisoformat(slots['end'])
        start_utc = start_dt.astimezone(pytz.UTC).isoformat()
        end_utc = end_dt.astimezone(pytz.UTC).isoformat()

        body = {
            "timeMin": start_utc,
            "timeMax": end_utc,
            "items": [{"id": calendar_id}]
        }

        response = service.freebusy().query(body=body).execute()
        busy_times = response['calendars'][calendar_id].get('busy', [])
        logger.info(f"Busy times: {busy_times}")

        return len(busy_times) == 0
    except HttpError as e:
        logger.error(f"Google API error: {e}")
    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
    return False

def book_appointment(slots: dict) -> bool:
    """
    Create an event in Google Calendar.
    Args:
        slots: dict with 'start', 'end', and optionally 'timezone'
    Returns:
        True if booking was successful, False otherwise.
    """
    logger.info(f"Booking appointment: {slots}")

    if not slots or 'start' not in slots or 'end' not in slots:
        logger.error("Invalid slots for booking")
        return False

    try:
        service, calendar_id = get_service_and_calendar_id()
        event = {
            'summary': 'Booked Appointment',
            'start': {'dateTime': slots['start'], 'timeZone': 'UTC'},
            'end': {'dateTime': slots['end'], 'timeZone': 'UTC'}
        }
        service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info("Event booked successfully.")
        return True
    except HttpError as e:
        logger.error(f"Booking API error: {e}")
    except Exception as e:
        logger.error(f"Booking failed: {str(e)}")
    return False
