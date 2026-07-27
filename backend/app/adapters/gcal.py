from datetime import datetime, timedelta, timezone

from googleapiclient.errors import HttpError

from app.adapters.errors import AdapterError
from app.adapters.google_auth import calendar_service
from app.adapters.retry import with_retry

CALENDAR_ID = "primary"


def _wrap(exc: HttpError) -> AdapterError:
    retryable = exc.resp.status >= 500 or exc.resp.status == 429
    return AdapterError(f"calendar api error {exc.resp.status}: {exc}", retryable=retryable)


@with_retry
def list_events(days: int = 7) -> list[dict]:
    svc = calendar_service()
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()
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
