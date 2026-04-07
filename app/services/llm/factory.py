from app.config import Settings
from app.exceptions import LLMConfigurationError, UnsupportedLLMProviderError
from app.services.llm.anthropic_provider import AnthropicLLMService
from app.services.llm.base import LLMService
from app.services.llm.mock_provider import MockLLMService
from app.services.llm.openai_provider import OpenAICompatibleLLMService
from app.services.llm.resilient_service import ResilientLLMService


def _build_base_service(settings: Settings) -> LLMService:
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return MockLLMService()
    if provider == "openai":
        if not settings.llm_api_key.strip() and not settings.llm_base_url.strip():
            raise LLMConfigurationError(
                "LLM_PROVIDER is 'openai' but neither LLM_API_KEY nor LLM_BASE_URL is set. "
                "Set LLM_API_KEY for OpenAI, or LLM_BASE_URL for a local OpenAI-compatible server "
                "(API key optional for many local gateways), or use LLM_PROVIDER=mock."
            )
        return OpenAICompatibleLLMService(settings)
    if provider == "anthropic":
        if not settings.llm_api_key.strip():
            raise LLMConfigurationError(
                "LLM_PROVIDER is 'anthropic' but LLM_API_KEY is missing or empty. "
                "Set LLM_API_KEY to your Anthropic API key and LLM_MODEL to a Claude model id."
            )
        return AnthropicLLMService(settings)
    raise UnsupportedLLMProviderError(settings.llm_provider)


def _infer_smaller_model(settings: Settings) -> str | None:
    provider = settings.llm_provider.lower().strip()
    model = settings.llm_model.strip()
    if provider == "openai" and model != "gpt-4o-mini":
        return "gpt-4o-mini"
    if provider == "anthropic" and "haiku" not in model.lower():
        return "claude-3-5-haiku-latest"
    return None


def get_llm_service(settings: Settings) -> LLMService:
    primary = _build_base_service(settings)
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return primary

    targets: list[LLMService] = [primary]
    fallback_model = _infer_smaller_model(settings)
    if fallback_model:
        smaller_settings = settings.model_copy(update={"llm_model": fallback_model})
        targets.append(_build_base_service(smaller_settings))
    targets.append(MockLLMService())
    return ResilientLLMService(*targets)
