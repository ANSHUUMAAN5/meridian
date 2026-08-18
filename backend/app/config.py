"""Runtime configuration, loaded from environment / .env.

Every tunable that the evaluation suite sweeps (the thresholds, top_k, chunk
sizes) lives here rather than as a constant in the code, so Sextant can vary
them without editing source.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "gemini", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── database ──
    # The application connects as a restricted role with no BYPASSRLS, so the
    # policies in migration 0001 actually apply. See scripts/create_app_role.py.
    database_url: str = "postgresql+asyncpg://localhost/meridian"
    # The owner role, used only by Alembic. Has BYPASSRLS — never used to serve
    # a request, or tenant isolation silently stops working.
    migration_database_url: str | None = None
    db_echo: bool = False

    # ── auth ──
    # Dev-only default, 32+ bytes so PyJWT does not warn. Production must
    # override it; see `insecure_jwt_secret` below.
    jwt_secret: str = "dev-only-insecure-secret-do-not-ship-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 1440

    # ── providers ──
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    compass_provider: Provider = "ollama"
    answer_provider: Provider = "ollama"

    # ── Threshold (§6.2). Defaults are starting points; the real values come
    #    from sweeping these against the golden set, not from intuition. ──
    tau_route: float = 0.75
    tau_answer: float = 0.70

    # ── retrieval ──
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    # bge-small is BERT-based and silently truncates at 512 tokens — verified
    # empirically: appending text past that point leaves the vector byte-identical.
    # Chunks must stay under it or their tails are embedded as nothing at all.
    embed_max_tokens: int = 512
    chunk_tokens: int = 400
    chunk_overlap: int = 80
    retrieve_top_k: int = 6


    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _normalise_pg_url(cls, v: str | None) -> str | None:
        """Accept a connection string copied verbatim from a Neon dashboard.

        Neon hands out a libpq-style URL. asyncpg speaks a different dialect,
        so rather than making a human remember three edits under time pressure
        (and debug a confusing driver error when they forget one), the
        translation happens here:

          postgresql://       -> postgresql+asyncpg://
          ?sslmode=require    -> ?ssl=require
          &channel_binding=.. -> dropped (libpq-only; asyncpg rejects it)
        """
        if not v:
            return v
        parts = urlsplit(v)

        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"

        keep: list[tuple[str, str]] = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "sslmode":
                keep.append(("ssl", "require" if value in ("require", "verify-full", "verify-ca") else value))
            elif key in ("channel_binding", "options", "application_name"):
                continue  # libpq-only; asyncpg raises on these
            else:
                keep.append((key, value))

        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(keep), parts.fragment))

    @property
    def insecure_jwt_secret(self) -> bool:
        """True when still running on the built-in development secret."""
        return self.jwt_secret.startswith("dev-only-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
