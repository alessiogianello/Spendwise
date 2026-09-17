from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which backend answers: Claude directly, or any model through OpenRouter.
    llm_provider: Literal["anthropic", "openrouter"] = "anthropic"
    # Model id. CLAUDE_MODEL is kept as an alias for existing .env files and
    # the eval runner's --model flag.
    model: str = Field("claude-opus-5", validation_alias=AliasChoices("LLM_MODEL", "CLAUDE_MODEL"))

    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None  # e.g. https://openrouter.ai/api for the Anthropic-compatible skin

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_reasoning_effort: str | None = None  # low | medium | high; unset = model default

    database_url: str = "sqlite:///./spendwise.db"
    demo_user_id: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
