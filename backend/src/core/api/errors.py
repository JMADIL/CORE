"""Translate storage failures to HTTP responses at the API boundary."""
from fastapi import Request
from fastapi.responses import JSONResponse
from core.storage.errors import (
    SessionError, SessionAccessDenied, SessionBusy,
    RateLimitExceeded, SessionCapacityExceeded,
)


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
