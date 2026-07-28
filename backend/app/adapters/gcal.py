from datetime import datetime, timedelta, timezone

from googleapiclient.errors import HttpError

from app.adapters.errors import AdapterError, wrap_google_error
from app.adapters.google_auth import calendar_service
from app.adapters.retry import with_retry

CALENDAR_ID = "primary"
IST = timezone(timedelta(hours=5, minutes=30))


def _wrap(exc: HttpError) -> AdapterError:
    return wrap_google_error(exc, "calendar")


@with_retry
def list_events(days: int = 7) -> list[dict]:
    svc = calendar_service()
    # anchor on the current week's Monday (IST), not "now" -- otherwise days earlier
    # in the week silently drop off the dashboard once their start time has passed
    today_ist = datetime.now(IST).date()
    week_start = datetime.combine(today_ist - timedelta(days=today_ist.weekday()), datetime.min.time(), tzinfo=IST)
    time_min = week_start.astimezone(timezone.utc).isoformat()
    time_max = (week_start + timedelta(days=days)).astimezone(timezone.utc).isoformat()
    try:
        resp = svc.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
        ).execute()
        return resp.get("items", [])
    except HttpError as e:
        raise _wrap(e)


@with_retry
def get_event(event_id: str) -> dict:
    svc = calendar_service()
    try:
        return svc.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def create_event(body: dict) -> dict:
    svc = calendar_service()
    try:
        return svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def move_event(event_id: str, new_start: str, new_end: str) -> dict:
    svc = calendar_service()
    try:
        return svc.events().patch(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body={
                "start": {"dateTime": new_start},
                "end": {"dateTime": new_end},
            },
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def delete_event(event_id: str) -> None:
    svc = calendar_service()
    try:
        svc.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def list_seeded_events() -> list[dict]:
    svc = calendar_service()
    try:
        resp = svc.events().list(
            calendarId=CALENDAR_ID,
            privateExtendedProperty="glanceSeed=1",
            singleEvents=True,
            maxResults=250,
        ).execute()
        return resp.get("items", [])
    except HttpError as e:
        raise _wrap(e)


@with_retry
def freebusy(start: str, end: str) -> dict:
    svc = calendar_service()
    try:
        return svc.freebusy().query(body={
            "timeMin": start,
            "timeMax": end,
            "items": [{"id": CALENDAR_ID}],
        }).execute()
    except HttpError as e:
        raise _wrap(e)
