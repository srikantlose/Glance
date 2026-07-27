from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ledger.models import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def mock_google_service(monkeypatch):
    """patches the service factory so adapter calls never hit the network."""
    from app.adapters import google_auth

    fake = MagicMock()
    monkeypatch.setattr(google_auth, "get_service", lambda name, version: fake)
    monkeypatch.setattr(google_auth, "gmail_service", lambda: fake)
    monkeypatch.setattr(google_auth, "calendar_service", lambda: fake)
    monkeypatch.setattr(google_auth, "tasks_service", lambda: fake)
    return fake


class FakeLyzr:
    def __init__(self):
        self.responses: dict[str, object] = {}
        self.calls: list[tuple] = []

    async def invoke(self, agent, payload, session_id):
        import inspect

        self.calls.append((agent, payload, session_id))
        value = self.responses.get(agent)

        if callable(value):
            result = value(payload)
            if inspect.isawaitable(result):
                result = await result
            return result
        if isinstance(value, list):
            if not value:
                raise AssertionError(f"fake_lyzr ran out of canned responses for agent={agent!r}")
            return value.pop(0)
        if value is None:
            raise AssertionError(f"no canned lyzr response configured for agent={agent!r}")
        return value


@pytest.fixture()
def fake_lyzr(monkeypatch):
    from app.agents import lyzr_client

    handle = FakeLyzr()
    monkeypatch.setattr(lyzr_client, "invoke", handle.invoke)
    return handle


def _hash_vector(text: str) -> list[float]:
    """centered around 0 so unrelated strings land near-orthogonal (low cosine) --
    a [0,1]-only range would give every pair of vectors a high baseline similarity
    just from sharing the same sign, which defeats threshold tests."""
    import hashlib

    h = hashlib.sha256(text.encode()).digest()
    return [(b - 128) / 128.0 for b in h[:16]]


@pytest.fixture()
def fake_embed(monkeypatch):
    """deterministic embeddings so cosine similarity in tests is predictable
    without calling out to gemini."""
    from app.memory import embeddings

    async def fake_embed_fn(texts):
        return [_hash_vector(t) for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed_fn)
    return _hash_vector


class _FakePoint:
    def __init__(self, point_id, vector, payload):
        self.id = point_id
        self.vector = vector
        self.payload = payload


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


class FakeQdrantClient:
    """dict-backed stand-in for AsyncQdrantClient -- enough surface area for the
    query/upsert/retrieve/scroll calls qdrant_client.py makes."""

    def __init__(self):
        self.collections: dict[str, dict[str, _FakePoint]] = {}

    async def get_collections(self):
        return SimpleNamespace(collections=[SimpleNamespace(name=n) for n in self.collections])

    async def create_collection(self, name, **kwargs):
        self.collections.setdefault(name, {})

    async def upsert(self, collection, points):
        store = self.collections.setdefault(collection, {})
        for p in points:
            store[str(p.id)] = _FakePoint(str(p.id), p.vector, dict(p.payload))

    async def retrieve(self, collection, ids, with_payload=True):
        store = self.collections.get(collection, {})
        return [store[str(i)] for i in ids if str(i) in store]

    async def set_payload(self, collection, payload, points):
        store = self.collections.get(collection, {})
        for i in points:
            if str(i) in store:
                store[str(i)].payload.update(payload)

    async def scroll(self, collection, limit=200, with_payload=True):
        store = self.collections.get(collection, {})
        return list(store.values())[:limit], None

    async def query_points(self, collection, query=None, prefetch=None, limit=10, with_payload=True, **kwargs):
        store = self.collections.get(collection, {})
        query_vector = prefetch[0].query if prefetch else query

        scored = []
        for p in store.values():
            vec = p.vector.get("dense") if isinstance(p.vector, dict) else p.vector
            score = _cosine(vec, query_vector) if vec and query_vector else 0.0
            scored.append(SimpleNamespace(id=p.id, score=score, payload=p.payload))
        scored.sort(key=lambda x: x.score, reverse=True)
        return SimpleNamespace(points=scored[:limit])


@pytest.fixture()
def fake_qdrant(monkeypatch):
    from app.memory import qdrant_client as qdrant_module

    fake = FakeQdrantClient()
    monkeypatch.setattr(qdrant_module, "get_client", lambda: fake)
    monkeypatch.setattr(qdrant_module, "sparse_vector", lambda text: object())
    return fake
