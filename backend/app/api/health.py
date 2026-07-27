from fastapi import APIRouter
from sqlalchemy import text

from app.db import SessionLocal
from app.memory.qdrant_client import get_client

router = APIRouter()


@router.get("/healthz")
async def healthz():
    db_ok = True
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_ok = False

    qdrant_ok = True
    try:
        await get_client().get_collections()
    except Exception:
        qdrant_ok = False

    return {"ok": db_ok and qdrant_ok, "db": db_ok, "qdrant": qdrant_ok}
