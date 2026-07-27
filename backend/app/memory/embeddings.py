from functools import lru_cache

from google import genai

from app.config import settings


@lru_cache(maxsize=None)
def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def embed(texts: list[str]) -> list[list[float]]:
    resp = await _client().aio.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=texts,
    )
    return [e.values for e in resp.embeddings]
