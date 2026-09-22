from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    """
    API Request schema for chat requests.
    """
    message: str
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    """
    API Response schema for health check.
    """
    status: str
    model: str
