from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-5"
    database_url: str = "sqlite:///./spendwise.db"
    demo_user_id: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
