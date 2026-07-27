import base64

from googleapiclient.errors import HttpError

from app import state
from app.adapters.errors import AdapterError, GoogleAuthError401
from app.adapters.google_auth import gmail_service
from app.adapters.retry import with_retry
from app.config import GMAIL_SEED_LABEL

USER_ID = "me"


def _check_failure_drill():
    if state.runtime_flags.get("failure_mode") == "gmail_401":
        raise GoogleAuthError401()


def _wrap(exc: HttpError) -> AdapterError:
    retryable = exc.resp.status >= 500 or exc.resp.status == 429
    return AdapterError(f"gmail api error {exc.resp.status}: {exc}", retryable=retryable)


@with_retry
def list_inbox(max_results: int = 20) -> list[dict]:
    _check_failure_drill()
    svc = gmail_service()
    try:
        resp = svc.users().messages().list(
            userId=USER_ID, labelIds=["INBOX"], maxResults=max_results
        ).execute()
        ids = [m["id"] for m in resp.get("messages", [])]
        return [get_message(i) for i in ids]
    except HttpError as e:
        raise _wrap(e)


@with_retry
def get_message(message_id: str) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    try:
        return svc.users().messages().get(userId=USER_ID, id=message_id, format="metadata",
                                           metadataHeaders=["From", "Subject", "Date"]).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def archive(message_id: str) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    try:
        return svc.users().messages().modify(
            userId=USER_ID, id=message_id, body={"removeLabelIds": ["INBOX"]}
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def unarchive(message_id: str) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    try:
        return svc.users().messages().modify(
            userId=USER_ID, id=message_id, body={"addLabelIds": ["INBOX"]}
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def label_add(message_id: str, label_id: str) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    try:
        return svc.users().messages().modify(
            userId=USER_ID, id=message_id, body={"addLabelIds": [label_id]}
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def label_remove(message_id: str, label_id: str) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    try:
        return svc.users().messages().modify(
            userId=USER_ID, id=message_id, body={"removeLabelIds": [label_id]}
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def send(to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
    _check_failure_drill()
    svc = gmail_service()
    raw = _build_rfc822(to, subject, body)
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    try:
        return svc.users().messages().send(userId=USER_ID, body=payload).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def insert_seed_message(raw_b64: str, label_ids: list[str]) -> dict:
    svc = gmail_service()
    try:
        return svc.users().messages().insert(
            userId=USER_ID, body={"raw": raw_b64, "labelIds": label_ids}
        ).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def delete_by_label(label_id: str) -> int:
    # trash, not delete -- messages.delete needs the full mail.google.com scope,
    # trash works fine with gmail.modify and has the same effect for reseeding
    svc = gmail_service()
    try:
        resp = svc.users().messages().list(userId=USER_ID, labelIds=[label_id], maxResults=100).execute()
        ids = [m["id"] for m in resp.get("messages", [])]
        for mid in ids:
            svc.users().messages().trash(userId=USER_ID, id=mid).execute()
        return len(ids)
    except HttpError as e:
        raise _wrap(e)


def find_label_id(name: str) -> str | None:
    svc = gmail_service()
    resp = svc.users().labels().list(userId=USER_ID).execute()
    for label in resp.get("labels", []):
        if label["name"] == name:
            return label["id"]
    return None


def ensure_label(name: str = GMAIL_SEED_LABEL) -> str:
    label_id = find_label_id(name)
    if label_id:
        return label_id
    svc = gmail_service()
    created = svc.users().labels().create(
        userId=USER_ID, body={"name": name, "labelListVisibility": "labelHide", "messageListVisibility": "show"}
    ).execute()
    return created["id"]


def _build_rfc822(to: str, subject: str, body: str) -> str:
    import email.mime.text

    msg = email.mime.text.MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()
