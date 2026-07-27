from functools import lru_cache

from fastembed import SparseTextEmbedding
from qdrant_client import AsyncQdrantClient, models

from app.config import settings, CONTEXT_TOP_K, EPISODE_TOP_K, POLICY_CANDIDATE_K
from app.memory import embeddings

PREFERENCES = "preferences"
EPISODES = "episodes"
CONTEXT = "context"


@lru_cache(maxsize=None)
def get_client() -> AsyncQdrantClient:
    # port has to be explicit -- leaving it out makes the client guess 443 and Qdrant Cloud 404s
    return AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, port=6333)


@lru_cache(maxsize=None)
def _bm25() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name="Qdrant/bm25")


def sparse_vector(text: str) -> models.SparseVector:
    embedding = next(_bm25().embed([text]))
    return models.SparseVector(indices=embedding.indices.tolist(), values=embedding.values.tolist())


async def search_preferences(text: str, k: int = POLICY_CANDIDATE_K) -> list[dict]:
    vector = (await embeddings.embed([text], task_type="RETRIEVAL_QUERY"))[0]
    client = get_client()
    hits = await client.query_points(PREFERENCES, query=vector, limit=k, with_payload=True)
    return [{"id": str(p.id), "score": p.score, **p.payload} for p in hits.points]


async def search_episodes(text: str, k: int = EPISODE_TOP_K) -> list[dict]:
    vector = (await embeddings.embed([text], task_type="RETRIEVAL_QUERY"))[0]
    client = get_client()
    hits = await client.query_points(EPISODES, query=vector, limit=k, with_payload=True)
    return [{"id": str(p.id), "score": p.score, **p.payload} for p in hits.points]


async def search_context_hybrid(text: str, k: int = CONTEXT_TOP_K) -> list[dict]:
    dense_vector = (await embeddings.embed([text], task_type="RETRIEVAL_QUERY"))[0]
    sparse = sparse_vector(text)
    client = get_client()
    hits = await client.query_points(
        CONTEXT,
        prefetch=[
            models.Prefetch(query=dense_vector, using="dense", limit=20),
            models.Prefetch(query=sparse, using="sparse", limit=20),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k,
        with_payload=True,
    )
    return [{"id": str(p.id), "score": p.score, **p.payload} for p in hits.points]


async def upsert_preference(point_id: str, text: str, payload: dict) -> None:
    vector = (await embeddings.embed([text], task_type="RETRIEVAL_DOCUMENT"))[0]
    client = get_client()
    await client.upsert(
        PREFERENCES,
        points=[models.PointStruct(id=point_id, vector=vector, payload={"text": text, **payload})],
    )


async def upsert_episode(point_id: str, text: str, payload: dict) -> None:
    vector = (await embeddings.embed([text], task_type="RETRIEVAL_DOCUMENT"))[0]
    client = get_client()
    await client.upsert(
        EPISODES,
        points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
    )


async def upsert_context(point_id: str, text: str, payload: dict) -> None:
    dense_vector = (await embeddings.embed([text], task_type="RETRIEVAL_DOCUMENT"))[0]
    sparse = sparse_vector(text)
    client = get_client()
    await client.upsert(
        CONTEXT,
        points=[models.PointStruct(
            id=point_id,
            vector={"dense": dense_vector, "sparse": sparse},
            payload=payload,
        )],
    )


async def increment_times_applied(point_id: str) -> None:
    client = get_client()
    points = await client.retrieve(PREFERENCES, ids=[point_id], with_payload=True)
    if not points:
        return
    payload = points[0].payload
    payload["times_applied"] = payload.get("times_applied", 0) + 1
    await client.set_payload(PREFERENCES, payload={"times_applied": payload["times_applied"]}, points=[point_id])


async def list_preferences() -> list[dict]:
    client = get_client()
    points, _ = await client.scroll(PREFERENCES, limit=200, with_payload=True)
    return [{"id": str(p.id), **p.payload} for p in points]
