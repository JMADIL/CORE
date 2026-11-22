"""HTTP authentication dependencies."""
import hashlib
import secrets
from fastapi import Header, HTTPException
from core.config import settings


def session_owner(x_client_token: str = Header(min_length=32, max_length=128), x_api_key: str = Header(default="")):
    if settings.CHAT_API_KEY and not secrets.compare_digest(x_api_key.encode(), settings.CHAT_API_KEY.encode()):
        raise HTTPException(401, "Invalid API key")
    return hashlib.sha256(x_client_token.encode()).hexdigest()
