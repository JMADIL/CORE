from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID

class ChatRequest(BaseModel):
    """
    API Request schema for chat requests.
    """
    message: str = Field(min_length=1, max_length=12000)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    request_id: UUID | None = None

    @field_validator("message")
    @classmethod
    def nonempty_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value

class CancelRequest(BaseModel):
    request_id: UUID


class HealthResponse(BaseModel):
    """
    API Response schema for health check.
    """
    status: str
    model: str
