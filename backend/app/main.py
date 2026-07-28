from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import account, actions, approvals, audit, command, dashboard, demo, health, policies, triage
from app.config import OUTBOX_POLL_SECONDS, settings
from app.memory.collections import ensure_collections
from app.workers.outbox_worker import run_outbox_pass

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collections()
    scheduler.add_job(run_outbox_pass, "interval", seconds=OUTBOX_POLL_SECONDS, id="outbox_worker")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="glance", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(account.router)
app.include_router(dashboard.router)
app.include_router(triage.router)
app.include_router(command.router)
app.include_router(actions.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(policies.router)
app.include_router(demo.router)
