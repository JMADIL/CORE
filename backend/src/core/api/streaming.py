"""SSE framing and provider text normalization."""
import json

from core.integrations.content import text_content


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
