from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
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
