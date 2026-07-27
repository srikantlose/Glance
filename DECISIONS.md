Running log of anything that deviated from the original plan. One line each, newest at the bottom.

2026-07-21 — renamed adapters/calendar.py to adapters/gcal.py (and tasks.py to gtasks.py) — calendar.py shadows the stdlib module and breaks the datetime imports it needs.
2026-07-21 — undo now bypasses the approval gate (execute_action skip_gate flag) — undoing an event.create means running event.delete, which is always gated, so without this every undo of a created event would just queue a second approval instead of actually undoing anything.
2026-07-21 — HoverLens Reply/Delegate go through POST /api/command with context.type="comms" instead of /api/actions/execute — those two need a drafted email first (comms agent + approval), so they can't be a plain tool/operation descriptor like archive or to-task. Same short-circuit pattern as conflict resolution. Delegate defaults to arjun@brightpath.co when no recipient is given, matching the seed data's cast.
