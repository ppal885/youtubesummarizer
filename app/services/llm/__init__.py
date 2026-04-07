from app.services.llm.base import LLMService
from app.services.llm.token_usage import estimate_token_count


def get_llm_service(settings):
    from app.services.llm.factory import get_llm_service as _get_llm_service

    return _get_llm_service(settings)


__all__ = ["LLMService", "estimate_token_count", "get_llm_service"]
