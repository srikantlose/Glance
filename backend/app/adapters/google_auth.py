from functools import lru_cache

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from app.config import settings


def _credentials() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=settings.google_scopes_list,
    )


@lru_cache(maxsize=None)
def get_service(name: str, version: str) -> Resource:
    return build(name, version, credentials=_credentials(), cache_discovery=False)


def gmail_service() -> Resource:
    return get_service("gmail", "v1")


def calendar_service() -> Resource:
    return get_service("calendar", "v3")


def tasks_service() -> Resource:
    return get_service("tasks", "v1")
