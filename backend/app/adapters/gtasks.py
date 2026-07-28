from googleapiclient.errors import HttpError

from app.adapters.errors import AdapterError, wrap_google_error
from app.adapters.google_auth import tasks_service
from app.adapters.retry import with_retry
from app.config import TASKS_LIST_NAME

_list_id_cache: str | None = None


def _wrap(exc: HttpError) -> AdapterError:
    return wrap_google_error(exc, "tasks")


def _list_id() -> str:
    global _list_id_cache
    if _list_id_cache:
        return _list_id_cache
    svc = tasks_service()
    resp = svc.tasklists().list().execute()
    for tl in resp.get("items", []):
        if tl["title"] == TASKS_LIST_NAME:
            _list_id_cache = tl["id"]
            return _list_id_cache
    created = svc.tasklists().insert(body={"title": TASKS_LIST_NAME}).execute()
    _list_id_cache = created["id"]
    return _list_id_cache


@with_retry
def list_tasks() -> list[dict]:
    svc = tasks_service()
    try:
        resp = svc.tasks().list(tasklist=_list_id(), showCompleted=True, showHidden=True).execute()
        return resp.get("items", [])
    except HttpError as e:
        raise _wrap(e)


@with_retry
def create_task(title: str, notes: str | None = None, due: str | None = None) -> dict:
    svc = tasks_service()
    body = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        # tasks API wants a full RFC3339 timestamp -- callers routinely only have a bare date
        body["due"] = due if "T" in due else f"{due}T00:00:00.000Z"
    try:
        return svc.tasks().insert(tasklist=_list_id(), body=body).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def complete_task(task_id: str) -> dict:
    svc = tasks_service()
    try:
        return svc.tasks().patch(tasklist=_list_id(), task=task_id, body={"status": "completed"}).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def uncomplete_task(task_id: str) -> dict:
    svc = tasks_service()
    try:
        return svc.tasks().patch(tasklist=_list_id(), task=task_id, body={"status": "needsAction"}).execute()
    except HttpError as e:
        raise _wrap(e)


@with_retry
def delete_task(task_id: str) -> None:
    svc = tasks_service()
    try:
        svc.tasks().delete(tasklist=_list_id(), task=task_id).execute()
    except HttpError as e:
        raise _wrap(e)


def clear_all_tasks() -> int:
    svc = tasks_service()
    try:
        resp = svc.tasks().list(tasklist=_list_id(), showCompleted=True, showHidden=True).execute()
        items = resp.get("items", [])
        for t in items:
            svc.tasks().delete(tasklist=_list_id(), task=t["id"]).execute()
        return len(items)
    except HttpError as e:
        raise _wrap(e)
