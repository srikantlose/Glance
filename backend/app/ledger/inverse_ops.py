"""hardcoded operation -> inverse map, per the frozen spec. don't get clever here --
undo correctness depends on this staying a dumb lookup table."""

EVENT_RECREATE_FIELDS = ("summary", "description", "start", "end", "attendees", "location")


def compute_inverse(
    tool: str, operation: str, params: dict, original: dict | None = None
) -> tuple[str | None, dict | None, bool]:
    """Returns (inverse_operation, inverse_params, irreversible).

    `original` is whatever pre-fetched state the inverse needs (e.g. the event body
    before a move/delete) -- the caller is responsible for fetching it before the
    action executes, since it won't be recoverable afterward.

    Inverse params referencing a not-yet-created resource id (event.create,
    task.create) carry a null placeholder that the caller patches in once the
    create call returns its id.
    """
    key = (tool, operation)

    if key == ("gmail", "send"):
        return None, None, True

    if key == ("gmail", "archive"):
        return "unarchive", {"message_id": params["message_id"]}, False
    if key == ("gmail", "unarchive"):
        return "archive", {"message_id": params["message_id"]}, False

    if key == ("gmail", "label.add"):
        return "label.remove", {"message_id": params["message_id"], "label_id": params["label_id"]}, False
    if key == ("gmail", "label.remove"):
        return "label.add", {"message_id": params["message_id"], "label_id": params["label_id"]}, False

    if key == ("calendar", "event.create"):
        return "event.delete", {"event_id": None}, False

    if key == ("calendar", "event.move"):
        if original is None:
            raise ValueError("event.move inverse needs the pre-move event body")
        return (
            "event.move",
            {
                "event_id": params["event_id"],
                "new_start": original["start"]["dateTime"],
                "new_end": original["end"]["dateTime"],
            },
            False,
        )

    if key == ("calendar", "event.delete"):
        if original is None:
            raise ValueError("event.delete inverse needs the full event body")
        body = {k: original[k] for k in EVENT_RECREATE_FIELDS if k in original}
        return "event.create", {"body": body}, False

    if key == ("tasks", "task.create"):
        return "task.delete", {"task_id": None}, False

    if key == ("tasks", "task.complete"):
        return "task.uncomplete", {"task_id": params["task_id"]}, False
    if key == ("tasks", "task.uncomplete"):
        return "task.complete", {"task_id": params["task_id"]}, False

    raise ValueError(f"no inverse mapping for {tool}.{operation}")


# operations whose inverse params contain a placeholder filled in after the create call returns
CREATE_OPS_NEEDING_ID_PATCH = {
    ("calendar", "event.create"): ("event_id", "id"),
    ("tasks", "task.create"): ("task_id", "id"),
}
