"""seeds the demo Gmail/Calendar/Tasks account. idempotent -- reseeding deletes
everything tagged as seeded and recreates it, so it's safe to run repeatedly."""

import base64
import email.mime.text
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters import gcal, gmail, gtasks  # noqa: E402
from app.config import GMAIL_SEED_LABEL  # noqa: E402

IST_OFFSET = timedelta(hours=5, minutes=30)

INTERNAL_DOMAIN = "brightpath.co"
PRIYA = f"priya@{INTERNAL_DOMAIN}"
ARJUN = f"arjun@{INTERNAL_DOMAIN}"
IT_OPS = f"it-ops@{INTERNAL_DOMAIN}"
PEOPLE = f"people@{INTERNAL_DOMAIN}"
MEERA = "meera@vendorco.in"
KIRAN = "kiran@apexretail.com"
SUNITA = "sunita@apexretail.com"
RAHUL = "rahul@northwind.co"

EMAILS = [
    dict(from_=MEERA, subject="URGENT: Q3 vendor performance report needed by Friday", unread=True, body=(
        "Hi Sam,\n\nWe need the Q3 vendor performance report ahead of our escalation call on Friday. "
        "Could you have it over by end of day Thursday? Happy to jump on a call if anything's unclear.\n\nThanks,\nMeera"
    )),
    dict(from_=MEERA, subject="Re: Invoice discrepancy on PO-1142", unread=True, body=(
        "Hi Sam,\n\nFollowing up on the credit note for PO-1142 -- the numbers still don't reconcile on our end. "
        "Can someone take a look today? This is holding up our month-end close.\n\nMeera"
    )),
    dict(from_=KIRAN, subject="Escalation: delivery slippage on the Pune order", unread=True, body=(
        "Sam,\n\nThe Pune order has slipped again and our warehouse team is asking questions. "
        "Can we get on a call today to sort this out? This is becoming a pattern.\n\nKiran"
    )),
    dict(from_=SUNITA, subject="Contract renewal — can we talk this week?", unread=False, body=(
        "Hi Sam,\n\nOur contract comes up for renewal next month and I wanted to get ahead of it. "
        "Do you have 30 minutes this week to talk through terms?\n\nBest,\nSunita"
    )),
    dict(from_="digest@saastimes.com", subject="SaaS Times Daily Digest #412", unread=False, body=(
        "Today's top stories in SaaS: pricing trends, three funding rounds, and a deep dive on churn.\n\n"
        "Read online or unsubscribe at any time.\n\n-- SaaS Times"
    )),
    dict(from_="hello@productweekly.io", subject="Product Weekly — 5 launches worth seeing", unread=False, body=(
        "This week: five product launches worth your attention, plus a roundup of roadmap tools.\n\n"
        "You're receiving this because you subscribed to Product Weekly. Unsubscribe anytime."
    )),
    dict(from_="news@techbrew.in", subject="TechBrew Morning Brief", unread=False, body=(
        "Good morning. Today's brief covers three funding announcements and a regulatory update.\n\n"
        "TechBrew Morning Brief -- unsubscribe from this list."
    )),
    dict(from_="updates@designdaily.co", subject="Design Daily: this week in interfaces", unread=False, body=(
        "This week in interface design: a roundup of new patterns, tools, and a case study on onboarding flows.\n\n"
        "Manage your subscription or unsubscribe."
    )),
    dict(from_="team@growthletter.com", subject="Growthletter #88", unread=False, body=(
        "Issue 88: retention tactics that actually moved the needle for three growth teams this quarter.\n\n"
        "Sent to subscribers of Growthletter. Unsubscribe here."
    )),
    dict(from_=PRIYA, subject="VEN-421: vendor onboarding blocked on compliance docs", unread=True, body=(
        "Hey Sam,\n\nVEN-421 is stuck -- compliance is waiting on the updated vendor docs from onboarding. "
        "Can you chase this before Friday's session? I don't want it slipping another week.\n\nPriya"
    )),
    dict(from_=ARJUN, subject="Re: VEN-421 — need Priya's sign-off before Thursday", unread=False, body=(
        "Sam,\n\nPicking up on VEN-421 -- I've got the checklist mostly done but need Priya's sign-off before "
        "Thursday to keep onboarding on schedule. Flagging in case you can nudge it along.\n\nArjun"
    )),
    dict(from_=PRIYA, subject="Weekly status — ops (week 30)", unread=False, body=(
        "Hi Sam,\n\nWeekly ops status: vendor onboarding is on track pending compliance sign-off, the Apex "
        "renewal conversation is scheduled, and the Q3 report is in progress. Nothing blocking otherwise.\n\nPriya"
    )),
    dict(from_=RAHUL, subject="Setting up time next week?", unread=True, body=(
        "Hi Sam,\n\nGreat meeting you through Meera's intro. Would love to find 30 minutes next week to talk "
        "through the Northwind engagement -- let me know what works on your end.\n\nRahul"
    )),
    dict(from_=RAHUL, subject="Re: intro from Meera — Northwind engagement", unread=False, body=(
        "Sam,\n\nThanks again for the intro chat. I'll put together a short brief on what we're proposing "
        "for the Northwind engagement and send it over before we speak.\n\nRahul"
    )),
    dict(from_=PRIYA, subject="Can we move our 1:1 this week?", unread=False, body=(
        "Hey Sam,\n\nSomething came up and I need to shuffle our 1:1 this week. Let me know a time that "
        "works and I'll resend the invite.\n\nPriya"
    )),
    dict(from_=KIRAN, subject="QBR scheduling — first week of August?", unread=False, body=(
        "Hi Sam,\n\nWanted to get ahead of scheduling -- does the first week of August work for the QBR? "
        "Let me know a couple of slots and I'll confirm with the team.\n\nKiran"
    )),
    dict(from_=IT_OPS, subject="Scheduled maintenance Saturday 02:00–04:00 IST", unread=False, body=(
        "This is a heads-up that we'll be performing scheduled maintenance on Saturday between 02:00 and "
        "04:00 IST. Brief service interruptions may occur. No action needed.\n\nIT Ops"
    )),
    dict(from_=PEOPLE, subject="Updated leave policy — action not required", unread=False, body=(
        "Hi all,\n\nWe've updated the leave policy doc with minor clarifications on carryover rules. "
        "No action is required on your part -- just sharing for visibility.\n\nPeople Team"
    )),
    dict(from_=IT_OPS, subject="Reminder: expense reports due end of month", unread=False, body=(
        "Reminder that expense reports for this month are due by the last business day. "
        "Reach out if you're missing any receipts.\n\nIT Ops"
    )),
    dict(from_=PEOPLE, subject="Office parking changes from next month", unread=False, body=(
        "Hi all,\n\nStarting next month, parking assignments are shifting to the north lot while the main "
        "lot is resurfaced. More details to follow closer to the date.\n\nPeople Team"
    )),
]

CALENDAR_EVENTS = [
    dict(day=0, start=(9, 30), end=(9, 45), title="Ops standup", attendees=[]),
    dict(day=0, start=(16, 0), end=(16, 30), title="Apex Retail check-in", attendees=[KIRAN]),
    dict(day=1, start=(9, 0), end=(11, 0), title="Deep Work", attendees=[]),
    dict(day=1, start=(9, 30), end=(10, 0), title="Vendor Sync", attendees=[PRIYA, ARJUN]),
    dict(day=2, start=(13, 0), end=(13, 30), title="Lunch block", attendees=[]),
    dict(day=2, start=(14, 0), end=(15, 0), title="Design review", attendees=[PRIYA, ARJUN]),
    dict(day=3, start=(15, 0), end=(15, 30), title="1:1 — Priya", attendees=[PRIYA]),
    dict(day=3, start=(15, 0), end=(15, 30), title="1:1 — Arjun", attendees=[ARJUN]),
    dict(day=4, start=(11, 30), end=(12, 0), title="Vendor onboarding — VEN-421", attendees=[MEERA]),
    dict(day=4, start=(15, 0), end=(16, 0), title="Sprint demo", attendees=[PRIYA, ARJUN]),
    dict(day=0, start=(11, 30), end=(12, 0), title="Weekly ops sync", attendees=[PRIYA, ARJUN]),
]

TASKS = [
    dict(title="Send Q3 vendor report to Meera", notes="Report requested for the Friday escalation call.", overdue=True),
    dict(title="Approve credit note for PO-1142", notes="Blocking Meera's month-end close.", overdue=True),
    dict(title="Prepare QBR deck for Apex", notes=None, overdue=False),
    dict(title="Review VEN-421 onboarding checklist", notes="Waiting on Priya's sign-off.", overdue=False),
    dict(title="Book travel for Bangalore offsite", notes=None, overdue=False),
    dict(title="Update the ops runbook", notes=None, overdue=False),
]


def _week_monday() -> date:
    today = date.today()
    if today.weekday() >= 5:  # Sat/Sun -> use next week
        return today + timedelta(days=7 - today.weekday())
    return today - timedelta(days=today.weekday())


def _ist_to_utc_iso(day: date, hour: int, minute: int) -> str:
    local = datetime.combine(day, time(hour, minute))
    return (local - IST_OFFSET).replace(tzinfo=timezone.utc).isoformat()


def _build_raw_message(from_addr: str, subject: str, body: str) -> str:
    msg = email.mime.text.MIMEText(body)
    msg["from"] = from_addr
    msg["to"] = "me"
    msg["subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def seed_gmail() -> int:
    label_id = gmail.ensure_label(GMAIL_SEED_LABEL)
    inbox_label_id = "INBOX"
    unread_label_id = "UNREAD"

    for item in EMAILS:
        raw = _build_raw_message(item["from_"], item["subject"], item["body"])
        label_ids = [label_id, inbox_label_id]
        if item["unread"]:
            label_ids.append(unread_label_id)
        gmail.insert_seed_message(raw, label_ids)

    return len(EMAILS)


def seed_calendar() -> int:
    monday = _week_monday()
    for ev in CALENDAR_EVENTS:
        day = monday + timedelta(days=ev["day"])
        body = {
            "summary": ev["title"],
            "start": {"dateTime": _ist_to_utc_iso(day, *ev["start"])},
            "end": {"dateTime": _ist_to_utc_iso(day, *ev["end"])},
            "extendedProperties": {"private": {"glanceSeed": "1"}},
        }
        if ev["attendees"]:
            body["attendees"] = [{"email": a} for a in ev["attendees"]]
        gcal.create_event(body)
    return len(CALENDAR_EVENTS)


def seed_tasks() -> int:
    today = date.today()
    for i, t in enumerate(TASKS):
        due = None
        if t["overdue"]:
            due = (today - timedelta(days=3)).isoformat() + "T00:00:00.000Z"
        gtasks.create_task(t["title"], t["notes"], due)
    return len(TASKS)


def clear_seeded() -> None:
    gmail.clear_inbox()

    for ev in gcal.list_seeded_events():
        gcal.delete_event(ev["id"])

    gtasks.clear_all_tasks()


def run_seed() -> dict:
    clear_seeded()
    counts = {
        "emails": seed_gmail(),
        "events": seed_calendar(),
        "tasks": seed_tasks(),
    }
    return counts


if __name__ == "__main__":
    result = run_seed()
    print(f"seeded {result['emails']} emails, {result['events']} calendar events, {result['tasks']} tasks")
