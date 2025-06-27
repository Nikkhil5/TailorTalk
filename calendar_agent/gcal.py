import streamlit as st
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
    Authenticate using credentials from Streamlit secrets.
    Returns:
        service: Google Calendar API service object
        calendar_id: The calendar ID to use for API calls
    """
    try:
        # Get credentials from secrets.toml
        credentials_info = dict(st.secrets["google_credentials"])
        calendar_id = st.secrets.get("CALENDAR_ID", "primary")
        
        creds = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)
        return service, calendar_id
    except Exception as e:
        logger.error(f"Credential loading failed: {str(e)}")
        raise

def check_availability(slots: dict) -> bool:
    """Check availability using Google Calendar FreeBusy API"""
    logger.info(f"Checking availability: {slots}")
    
    # Validate slots
    if not slots or 'start' not in slots or 'end' not in slots:
        logger.error("Invalid slots format")
        return False
    
    try:
        service, calendar_id = get_service_and_calendar_id()
        
        # Convert to datetime objects
        start_dt = datetime.fromisoformat(slots['start'])
        end_dt = datetime.fromisoformat(slots['end'])
        
        # Handle timezones
        if start_dt.tzinfo is None:
            user_tz = pytz.timezone(slots.get('timezone', 'Asia/Kolkata'))
            start_dt = user_tz.localize(start_dt)
            end_dt = user_tz.localize(end_dt)
        
        # Convert to UTC
        start_utc = start_dt.astimezone(pytz.UTC).isoformat()
        end_utc = end_dt.astimezone(pytz.UTC).isoformat()
        
        # Prepare API request
        body = {
            "timeMin": start_utc,
            "timeMax": end_utc,
            "items": [{"id": calendar_id}]
        }
        
        # Execute request
        response = service.freebusy().query(body=body).execute()
        busy_times = response['calendars'][calendar_id].get('busy', [])
        
        return len(busy_times) == 0
    except HttpError as e:
        logger.error(f"Google API error: {e}")
    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
    
    return False

def book_appointment(slots: dict) -> bool:
    """Create calendar event"""
    logger.info(f"Booking appointment: {slots}")
    
    # Validate slots
    if not slots or 'start' not in slots or 'end' not in slots:
        logger.error("Invalid slots for booking")
        return False
    
    try:
        # Get service and calendar ID
        service, calendar_id = get_service_and_calendar_id()
        
        # Prepare event with timezone
        timezone = slots.get('timezone', 'UTC')
        event = {
            'summary': 'Booked Appointment',
            'start': {
                'dateTime': slots['start'],
                'timeZone': timezone
            },
            'end': {
                'dateTime': slots['end'],
                'timeZone': timezone
            }
        }
        
        # Execute booking
        service.events().insert(calendarId=calendar_id, body=event).execute()
        return True
    except HttpError as e:
        logger.error(f"Booking API error: {e}")
    except Exception as e:
        logger.error(f"Booking failed: {str(e)}")
    
    return False
