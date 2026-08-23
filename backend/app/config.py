from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "gemini", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://localhost/meridian"
    migration_database_url: str | None = None
    db_echo: bool = False

    jwt_secret: str = "dev-only-insecure-secret-do-not-ship-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 1440

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    answer_provider: Provider = "ollama"

    tau_route: float = 0.75
    tau_answer: float = 0.70

    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    embed_max_tokens: int = 512
    chunk_tokens: int = 400
    chunk_overlap: int = 80
    retrieve_top_k: int = 6

    demo_tenant_slugs: list[str] = ["kite", "nimbus"]


    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _normalise_pg_url(cls, v: str | None) -> str | None:
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
                continue
            else:
                keep.append((key, value))

        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(keep), parts.fragment))

    @property
    def insecure_jwt_secret(self) -> bool:
        return self.jwt_secret.startswith("dev-only-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
