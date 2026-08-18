"""Runtime configuration, loaded from environment / .env.

Every tunable that the evaluation suite sweeps (the thresholds, top_k, chunk
sizes) lives here rather than as a constant in the code, so Sextant can vary
them without editing source.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "gemini", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── database ──
    database_url: str = "postgresql+asyncpg://localhost/meridian"
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
    chunk_tokens: int = 600
    chunk_overlap: int = 80
    retrieve_top_k: int = 6


    @property
    def insecure_jwt_secret(self) -> bool:
        """True when still running on the built-in development secret."""
        return self.jwt_secret.startswith("dev-only-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
