"""ASGI entrypoint for the YouTube Video Copilot API (FastAPI app + router wiring)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_tracing import RequestTracingMiddleware
from app.db.session import init_db
from app.observability.ask_pipeline import configure_ask_pipeline_logging
from app.observability.llm_calls import configure_llm_call_logging
from app.observability.request_tracing import configure_request_tracing_logging
from app.observability.summarize_pipeline import configure_summarize_pipeline_logging
from app.models.response_models import HealthResponse, RootResponse
from app.routers.ask import router as ask_router
from app.routers.compare import router as compare_router
from app.routers.synthesize import router as synthesize_router
from app.routers.config_public import router as config_public_router
from app.routers.learning import router as learning_router
from app.routers.summarize import router as summarize_router
from app.services.summary_job_service import build_default_summary_job_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_request_tracing_logging()
    configure_ask_pipeline_logging()
    configure_llm_call_logging()
    configure_summarize_pipeline_logging()
    init_db()
    build_default_summary_job_service(settings).recover_incomplete_jobs()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.include_router(summarize_router, prefix="/api/v1", tags=["summarize"])
app.include_router(compare_router, prefix="/api/v1", tags=["compare"])
app.include_router(synthesize_router, prefix="/api/v1", tags=["synthesize"])
app.include_router(ask_router, prefix="/api/v1", tags=["qa"])
app.include_router(learning_router, prefix="/api/v1", tags=["learning"])
app.include_router(config_public_router, prefix="/api/v1", tags=["config"])

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# Order (last added = outermost): tracing wraps rate limit + CORS so totals cover the full stack.
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.rate_limit_enabled,
    requests_per_minute=settings.rate_limit_requests_per_minute,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware)


@app.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(
        message="YouTube Video Copilot API",
        version=settings.app_version,
        docs="/docs",
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()
