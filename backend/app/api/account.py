from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.adapters.google_auth import gmail_service
from app.config import settings

router = APIRouter()

# there is no per-user session here -- the whole app runs against one refresh token, so
# the address behind it is fixed for the life of the process. one profile call, cached.
_identity: dict = {}

_SERVICES = [("Gmail", "gmail"), ("Calendar", "calendar"), ("Tasks", "tasks")]


def _fetch_email() -> str:
    return gmail_service().users().getProfile(userId="me").execute()["emailAddress"]


@router.get("/api/account")
async def get_account():
    error = None
    if "email" not in _identity:
        try:
            _identity["email"] = await run_in_threadpool(_fetch_email)
        except Exception as exc:
            # a dead token shouldn't take the nav down with it, so report instead of raising
            error = str(exc)

    scopes = settings.google_scopes_list
    services = []
    for label, key in _SERVICES:
        granted = next((s for s in scopes if f"/auth/{key}" in s), None)
        services.append({
            "name": label,
            "granted": granted is not None,
            "scope": granted.rsplit("/auth/", 1)[-1] if granted else None,
        })

    return {
        "email": _identity.get("email"),
        "connected": "email" in _identity,
        "error": error,
        "services": services,
    }
