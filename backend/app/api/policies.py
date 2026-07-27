from fastapi import APIRouter

from app.memory.qdrant_client import list_preferences

router = APIRouter()


@router.get("/api/policies")
async def get_policies():
    return await list_preferences()
