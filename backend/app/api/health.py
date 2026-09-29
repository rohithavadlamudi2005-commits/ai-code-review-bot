from typing import Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.config import get_settings
from app.llm.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


class GeminiHealthResponse(BaseModel):
    connected: bool
    model: str
    error: Optional[str] = None


class FullHealthResponse(BaseModel):
    status: str
    service: str
    components: Dict[str, Any]


def get_gemini_provider() -> GeminiProvider:
    """Dependency provider for GeminiProvider."""
    return GeminiProvider()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the operational health status of the AI Code Review Bot service."
)
async def get_health() -> HealthResponse:
    """
    Health check endpoint returning backend status.
    """
    return HealthResponse(
        status="ok",
        service="ai-code-review-bot"
    )


@router.get(
    "/health/gemini",
    response_model=GeminiHealthResponse,
    summary="Gemini Health Diagnostic",
    description="Safely verify connectivity and status of the configured Gemini LLM provider."
)
async def get_gemini_health(
    provider: GeminiProvider = Depends(get_gemini_provider)
) -> GeminiHealthResponse:
    """
    Returns connection status of Gemini API without exposing credentials.
    """
    try:
        res = await provider.test_connection()
        return GeminiHealthResponse(
            connected=bool(res.get("connected", False)),
            model=str(res.get("model", "gemini-3.5-flash")),
            error=res.get("error")
        )
    except Exception as exc:
        logger.warning("Gemini health check error: %s", str(exc))
        settings = get_settings()
        return GeminiHealthResponse(
            connected=False,
            model=getattr(provider, "model", settings.GEMINI_MODEL),
            error=f"Health check failed: {str(exc)}"
        )


@router.get(
    "/health/full",
    response_model=FullHealthResponse,
    summary="Full Component Health Check",
    description="Inspect overall health of backend, Redis, Celery, and Gemini components."
)
async def get_full_health(
    provider: GeminiProvider = Depends(get_gemini_provider)
) -> FullHealthResponse:
    settings = get_settings()

    try:
        gemini_res = await provider.test_connection()
    except Exception as exc:
        logger.warning("Full health check Gemini error: %s", str(exc))
        gemini_res = {
            "connected": False,
            "model": getattr(provider, "model", settings.GEMINI_MODEL),
            "error": f"Health check failed: {str(exc)}"
        }

    redis_status = "disabled"
    if settings.USE_CELERY or settings.REDIS_URL:
        try:
            import redis
            r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
            if r.ping():
                redis_status = "ok"
            else:
                redis_status = "unavailable"
        except Exception:
            redis_status = "unavailable"

    gemini_info: Dict[str, Any] = {
        "connected": bool(gemini_res.get("connected", False)),
        "model": str(gemini_res.get("model", settings.GEMINI_MODEL)),
    }
    if gemini_res.get("error"):
        gemini_info["error"] = gemini_res["error"]

    return FullHealthResponse(
        status="ok",
        service="ai-code-review-bot",
        components={
            "gemini": gemini_info,
            "redis": {
                "status": redis_status
            },
            "celery": {
                "enabled": settings.USE_CELERY
            }
        }
    )


