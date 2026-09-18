from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenRouter model id in vendor/model form, e.g. anthropic/claude-sonnet-5
    # or openai/gpt-5.4-mini (full list: openrouter.ai/models).
    model: str = Field("anthropic/claude-opus-5", validation_alias="LLM_MODEL")

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_reasoning_effort: str | None = None  # low | medium | high; unset = model default

    database_url: str = "sqlite:///./spendwise.db"
    demo_user_id: int = 1

    # Shared passphrase for the hosted demo, sent as X-Demo-Password by the
    # client. Unset (the local default) means the API is open.
    demo_password: str | None = None
    # Flutter web build to serve at "/" when the directory exists (see Dockerfile).
    static_dir: str = "static"


@lru_cache
def get_settings() -> Settings:
    return Settings()
