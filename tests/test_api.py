import asyncio
import json
from fastapi.testclient import TestClient
from src.api.app import app
from src.config import settings

# Temporarily use google/gemini-2.5-flash for testing to prevent OpenRouter 429
settings.LLM_MODEL = "google/gemini-2.5-flash"

client = TestClient(app)

def test_health_endpoint():
    """
    Test that the health endpoint returns the correct status and model name.
    """
    print("\nTesting GET /health...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model"] == "google/gemini-2.5-flash"
    print("Health check passed:", data)

def test_chat_streaming():
    """
    Test that the /api/chat endpoint streams valid Server-Sent Events (SSE).
    """
    print("\nTesting POST /api/chat streaming...")
    payload = {
        "message": "What is the current time in Tokyo?"
    }
    
    events_received = []
    tokens_received = []
    
    # Use client.stream to read chunked/streamed response
    with client.stream("POST", "/api/chat", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        current_event = None
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.strip()
            if line_str.startswith("event:"):
                current_event = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("data:") and current_event:
                data_json = line_str.split(":", 1)[1].strip()
                data = json.loads(data_json)
                
                print(f"SSE [{current_event}]: {data}")
                events_received.append(current_event)
                
                if current_event == "token":
                    tokens_received.append(data["token"])
                
                current_event = None
                
    # Assertions
    assert "agent_state" in events_received
    assert "done" in events_received
    # We should have received conversational tokens from the responder
    assert len(tokens_received) > 0
    full_response = "".join(tokens_received)
    print("\nFull response from responder:", repr(full_response))
    assert len(full_response) > 5

if __name__ == "__main__":
    test_health_endpoint()
    try:
        test_chat_streaming()
    except Exception as e:
        print(f"Error testing chat streaming: {e}")
