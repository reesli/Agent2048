"""Configuration via environment variables and .env.

.env values override shell environment variables so the active project config
always wins."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


_ENV_CANDIDATES = [
    Path(".env"),
    Path.home() / ".config" / "agent2048" / ".env",
]


class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    model: str = Field("gpt-4o-mini", alias="MODEL")
    embedding_provider: str = Field("fastembed", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field("BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    db_path: str = Field("", alias="DB_PATH")
    max_context_tokens: int = Field(200000, alias="MAX_CONTEXT_TOKENS")
    merge_similarity_threshold: float = Field(0.82, alias="MERGE_SIMILARITY_THRESHOLD")
    max_steps: int = Field(1000, alias="MAX_STEPS")
    max_merge_depth: int = Field(4, alias="MAX_MERGE_DEPTH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def _load_dotenv_files() -> None:
    """Reload .env files with override so project config wins over env vars."""
    for candidate in _ENV_CANDIDATES:
        if candidate.exists():
            load_dotenv(candidate, override=True)


class MutableSettings:
    """Wrapper that lets us reload .env at runtime without re-importing modules."""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        _load_dotenv_files()
        self._settings = Settings()

    def __getattr__(self, name: str) -> object:
        return getattr(self._settings, name)


settings = MutableSettings()
