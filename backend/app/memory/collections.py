import uuid

from qdrant_client import models

from app.config import settings
from app.memory.qdrant_client import get_client

PREFERENCES = "preferences"
EPISODES = "episodes"
CONTEXT = "context"


def pref_id(n: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"glance/pref/{n}"))


def episode_id(n: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"glance/episode/{n}"))


def context_id(source: str, source_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"glance/context/{source}/{source_id}"))


async def ensure_collections() -> None:
    client = get_client()
    existing = {c.name for c in (await client.get_collections()).collections}

    if PREFERENCES not in existing:
        await client.create_collection(
            PREFERENCES,
            vectors_config=models.VectorParams(size=settings.EMBED_DIM, distance=models.Distance.COSINE),
        )

    if EPISODES not in existing:
        await client.create_collection(
            EPISODES,
            vectors_config=models.VectorParams(size=settings.EMBED_DIM, distance=models.Distance.COSINE),
        )

    if CONTEXT not in existing:
        await client.create_collection(
            CONTEXT,
            vectors_config={
                "dense": models.VectorParams(size=settings.EMBED_DIM, distance=models.Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF),
            },
        )
