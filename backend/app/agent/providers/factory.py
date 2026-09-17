from app.agent.providers.base import LLMProvider, ProviderError
from app.config import Settings


def create_provider(settings: Settings) -> LLMProvider:
    """Builds the provider selected by LLM_PROVIDER. Import lazily so the
    Anthropic SDK is not required to run against OpenRouter and vice versa."""
    match settings.llm_provider:
        case "anthropic":
            from app.agent.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(
                model=settings.model,
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url,
            )
        case "openrouter":
            from app.agent.providers.openrouter_provider import OpenRouterProvider

            if not settings.openrouter_api_key:
                raise ProviderError("OPENROUTER_API_KEY non impostata (backend/.env).")
            if "/" not in settings.model:
                raise ProviderError(
                    f"'{settings.model}' non è un id OpenRouter: usa il formato vendor/model, "
                    "es. LLM_MODEL=anthropic/claude-sonnet-5 oppure openai/gpt-5.4-mini."
                )
            return OpenRouterProvider(
                model=settings.model,
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                reasoning_effort=settings.openrouter_reasoning_effort or None,
            )
    raise ProviderError(f"LLM_PROVIDER sconosciuto: {settings.llm_provider!r} (anthropic | openrouter)")
