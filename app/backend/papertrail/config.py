from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


_ENV_FILE = _env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE is not None else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    token_factory_api_key: str = ""
    token_factory_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    chat_model_small: str = ""
    chat_model_large: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 1024

    database_url: str = "postgresql+psycopg://papertrail:papertrail@localhost:5432/papertrail"
    scholarly_contact_email: str = ""
    openalex_api_key: str = ""

    max_candidates: int = 3
    max_llm_calls_per_run: int = 12
    max_planner_iterations: int = 8
    prefilter_limit: int = 15
    cors_origins: str = "http://localhost:5173"

    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
