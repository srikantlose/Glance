# Glance

A hover-first executive assistant for Gmail, Calendar and Tasks. Hover a message, event or task and it tells you what it would do and why — cites the policy it's acting on, or asks one question if it doesn't know your preference yet.

Live: TBD
Demo video: TBD

## What this is

Three inbox-style columns (mail, calendar, tasks) with a command bar on top. Everything the assistant does — archiving, scheduling, drafting, delegating — goes through a policy gate first: if it matches something you've told it before, it acts and shows you the policy it used. If not, it asks once, and remembers the answer.

## Architecture

```
Next.js (Vercel) -> FastAPI (Railway) -> Lyzr agents (Gemini) -> Google APIs
                                       -> Postgres ledger
                                       -> Qdrant memory
```

More detail once the diagram is drawn (Day 7).

## Stack

- **Gemini** — the reasoning behind every triage verdict, scheduling option, draft and policy decision. Flash on the hover path for latency, Pro for planning and drafting.
- **Lyzr** — orchestrates the five agents (manager, triage, scheduler, comms, policy gate), plus guardrails and trace IDs.
- **Qdrant** — memory. Preferences, past scheduling decisions, and hybrid search over the inbox so triage can cite real context.

Full "why each one matters" writeup goes in here Day 7.

## Setup

Copy `.env.example` to `.env` and fill in the values (see `EXECUTION_PLAN.md` locally for where each one comes from — not part of this repo).

```
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

```
cd frontend
npm install
npm run dev
```

Seed the demo account:

```
python scripts/seed.py
python scripts/seed_memory.py
```

## Audit trail

Every action the assistant takes writes a row to the ledger before it reports success — actor, tool, operation, what authorized it (a policy, an instruction, or an approval), and a precomputed inverse so it can be undone. Sends are the one exception: irreversible, flagged as such, no undo.

## Notes on the seed data

The demo account is a fictional ops lead ("Sam") at a company called Brightpath. The inbox has a couple of newsletters (auto-archive demo), a client request that needs delegating, and two calendar conflicts on purpose. Reseed any time with `POST /api/demo/reseed`.
