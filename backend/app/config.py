import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GEMINI_API_KEY: str = ""
    GEMINI_FLASH_MODEL: str = ""
    GEMINI_PRO_MODEL: str = ""
    GEMINI_EMBED_MODEL: str = ""
    EMBED_DIM: int = 0

    LYZR_API_KEY: str = ""
    LYZR_BASE_URL: str = ""
    LYZR_MANAGER_AGENT_ID: str = ""
    LYZR_AGENT_IDS_JSON: str = "{}"

    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    DATABASE_URL: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""
    GOOGLE_SCOPES: str = (
        "https://www.googleapis.com/auth/gmail.modify,"
        "https://www.googleapis.com/auth/calendar,"
        "https://www.googleapis.com/auth/tasks"
    )

    DEMO_FAILURE_MODE: str = "off"
    DEMO_TOKEN: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        # railway hands out postgres:// or postgresql://, sqlalchemy+psycopg3 wants the +psycopg driver
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+psycopg" not in v:
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @property
    def lyzr_agent_ids(self) -> dict:
        return json.loads(self.LYZR_AGENT_IDS_JSON or "{}")

    @property
    def google_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.GOOGLE_SCOPES.split(",") if s.strip()]


settings = Settings()

# pinned constants — not env, not overridable per-deploy
POLICY_MATCH_THRESHOLD = 0.67  # calibrated against live gemini-embedding-001 scores, see DECISIONS.md
POLICY_CANDIDATE_K = 5
CONTEXT_TOP_K = 6
EPISODE_TOP_K = 4
HOVER_LATENCY_BUDGET_MS = 1500
ADAPTER_MAX_RETRIES = 3
OUTBOX_POLL_SECONDS = 30
HYBRID_FUSION = "rrf"

INTERNAL_DOMAINS = {"brightpath.co"}
TRIAGE_CACHE_TTL_S = 600
DASHBOARD_CACHE_TTL_S = 60
CLARIFICATION_MATCH_THRESHOLD = 0.85
OUTBOX_DEAD_AFTER_ATTEMPTS = 10
PREWARM_CONCURRENCY = 8

GMAIL_SEED_LABEL = "glance-seed"
TASKS_LIST_NAME = "Glance Demo"
LYZR_USER_ID = "glance-demo"
LYZR_CHAT_PATH = "/v3/inference/chat/"

# one-click Delegate on the hover card needs somewhere to delegate TO -- Arjun is the
# designated delegation target in the seed data (see scripts/seed.py)
DEFAULT_DELEGATE_EMAIL = "arjun@brightpath.co"
DEFAULT_DELEGATE_DUE_DAYS = 3
