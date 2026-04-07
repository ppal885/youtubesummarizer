from fastapi import APIRouter

from app.config import settings
from app.demo.catalog import DEMO_VIDEO_URL
from app.models.response_models import PublicConfigResponse, PublicLlmConfig

router = APIRouter()


def _llm_public_config() -> PublicLlmConfig:
    provider = settings.llm_provider.lower().strip()
    key_set = bool(settings.llm_api_key.strip())
    base_set = bool(settings.llm_base_url.strip())

    if provider == "mock":
        configured = True
    elif provider == "openai":
        configured = key_set or base_set
    elif provider == "anthropic":
        configured = key_set
    else:
        configured = False

    return PublicLlmConfig(
        provider=provider,
        model=settings.llm_model,
        configured=configured,
        base_url_custom=base_set,
        json_response_format=settings.llm_json_response_format,
    )


@router.get("/config", response_model=PublicConfigResponse)
def get_public_config() -> PublicConfigResponse:
    return PublicConfigResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        llm=_llm_public_config(),
        demo_mode=settings.demo_mode,
        demo_sample_video_url=DEMO_VIDEO_URL if settings.demo_mode else None,
    )
