from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'test.json'  # or use your env/secret method
CALENDAR_ID = 'primary'  # or your calendar ID

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

events_result = service.events().list(
    calendarId=CALENDAR_ID,
    maxResults=5,
    singleEvents=True,
    orderBy='startTime'
).execute()

events = events_result.get('items', [])
if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(start, event['summary'])
