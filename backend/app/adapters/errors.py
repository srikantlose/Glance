class AdapterError(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


# google signals rate limiting with a 403 and one of these reasons, not a 429 -- a
# burst of event creates during reseed trips it, and treating it as permanent meant
# the whole reseed died instead of backing off
_RATE_LIMIT_REASONS = {"ratelimitexceeded", "userratelimitexceeded", "quotaexceeded"}


def wrap_google_error(exc, api: str) -> AdapterError:
    """shared by the gmail/calendar/tasks adapters so they agree on what's worth retrying."""
    status = exc.resp.status
    retryable = status >= 500 or status == 429
    if status == 403:
        reasons = {d.get("reason", "").lower() for d in getattr(exc, "error_details", None) or []}
        retryable = bool(reasons & _RATE_LIMIT_REASONS)
    return AdapterError(f"{api} api error {status}: {exc}", retryable=retryable)


class GoogleAuthError401(AdapterError):
    """raised by the gmail adapter when the failure-drill flag is on, before any real request goes out"""

    def __init__(self):
        super().__init__("gmail auth failed (401) — demo failure mode is on", retryable=True)
