"""Translate storage failures to HTTP responses at the API boundary."""
from fastapi import Request
from fastapi.responses import JSONResponse
from core.storage.errors import (
    SessionError, SessionAccessDenied, SessionBusy,
    RateLimitExceeded, SessionCapacityExceeded,
)


def chat_error_response(error: Exception) -> dict[str, str]:
    """Translate provider limits without exposing raw responses or credentials."""
    from core.integrations.elevenlabs import ElevenLabsUnavailable, ElevenLabsImageLimit
    if isinstance(error, RateLimitExceeded):
        return {"code": "media_demo_limit", "detail": str(error)}
    if isinstance(error, (ElevenLabsUnavailable, ElevenLabsImageLimit)):
        return {"code": error.code, "detail": error.detail}
    if getattr(error, "status_code", None) == 429 or getattr(error, "code", None) == 429:
        body = getattr(error, "body", None)
        details = body.get("error", body) if isinstance(body, dict) else {}
        details = details if isinstance(details, dict) else {}
        metadata = details.get("metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        if (metadata.get("limit_source") == "openrouter_free_tier_daily"
                or "free-models-per-day" in str(details.get("message", ""))):
            return {
                "code": "model_daily_limit",
                "detail": "We've reached our AI model's daily usage limit. Please try again after the daily reset.",
            }
        return {
            "code": "model_rate_limit",
            "detail": "We've reached the AI model's request limit. Please wait a little and try again.",
        }
    return {"detail": "Unable to complete the response. Please try again."}


async def session_error_response(request: Request, error: SessionError):
    codes = {
        SessionAccessDenied: 403,
        SessionBusy: 409,
        RateLimitExceeded: 429,
        SessionCapacityExceeded: 503,
    }
    return JSONResponse(
        {"detail": str(error)}, status_code=codes.get(type(error), 500),
        headers={"Retry-After": "60"} if isinstance(error, RateLimitExceeded) else None,
    )
