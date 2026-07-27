from functools import lru_cache

from google import genai
from google.genai import types

from app.config import settings


@lru_cache(maxsize=None)
def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def embed(texts: list[str], task_type: str | None = None) -> list[list[float]]:
    # gemini-embedding-001 needs the asymmetric task_type set or cosine scores between a
    # short instruction and a short stored policy sit around 0.5-0.7, well under any
    # sane match threshold -- see DECISIONS.md
    config = types.EmbedContentConfig(task_type=task_type) if task_type else None
    resp = await _client().aio.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=texts,
        config=config,
    )
    return [e.values for e in resp.embeddings]
