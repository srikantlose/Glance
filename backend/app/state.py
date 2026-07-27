import time

from app.config import settings, DASHBOARD_CACHE_TTL_S, TRIAGE_CACHE_TTL_S

# runtime-toggleable flags, e.g. the gmail_401 failure drill — separate from the env default
# so /api/demo/failure-mode can flip it without a restart
runtime_flags = {"failure_mode": settings.DEMO_FAILURE_MODE}

# message_id -> (verdict_dict, expires_at_epoch)
triage_cache: dict[str, tuple[dict, float]] = {}

# (snapshot_dict, expires_at_epoch) | None
dashboard_cache: tuple[dict, float] | None = None


def get_triage_cached(message_id: str) -> dict | None:
    entry = triage_cache.get(message_id)
    if entry is None:
        return None
    verdict, expires_at = entry
    if time.time() > expires_at:
        triage_cache.pop(message_id, None)
        return None
    return verdict


def set_triage_cached(message_id: str, verdict: dict) -> None:
    triage_cache[message_id] = (verdict, time.time() + TRIAGE_CACHE_TTL_S)


def get_dashboard_cached() -> dict | None:
    global dashboard_cache
    if dashboard_cache is None:
        return None
    snapshot, expires_at = dashboard_cache
    if time.time() > expires_at:
        dashboard_cache = None
        return None
    return snapshot


def set_dashboard_cached(snapshot: dict) -> None:
    global dashboard_cache
    dashboard_cache = (snapshot, time.time() + DASHBOARD_CACHE_TTL_S)


def clear_caches() -> None:
    global dashboard_cache
    triage_cache.clear()
    dashboard_cache = None
