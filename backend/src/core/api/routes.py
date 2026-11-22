"""HTTP routes and streaming transport for graph execution."""
import asyncio
import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from core.api.dependencies import session_owner
from core.api.schemas import ChatRequest, CancelRequest, HealthResponse
from core.api.cancellation import cancellable_events
from core.api.streaming import sse, text_content
from core.config import settings
from core.integrations.llm import model_name
from core.storage.history import trim_history

logger = logging.getLogger("api")
router = APIRouter()


@router.get("/")
async def root():
    return {"status": "ok", "endpoints": {"health": "/health", "chat": "/api/chat", "docs": "/docs"}}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", model=model_name())


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request, owner: str = Depends(session_owner)):
    await asyncio.to_thread(request.app.state.sessions.delete, session_id, owner)
    return Response(status_code=204)


@router.post("/api/chat")
async def chat_endpoint(payload: ChatRequest, request: Request, owner: str = Depends(session_owner)):
    session_id = payload.session_id or str(uuid.uuid4())
    # Configure ASGI's trusted proxy list at deployment; never read arbitrary forwarding headers here.
    client = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
    store = request.app.state.sessions
    lease, messages = await asyncio.to_thread(store.claim, session_id, owner, client, str(payload.request_id) if payload.request_id else None)
    initial_state = {
        "messages": trim_history(messages + [HumanMessage(content=payload.message)]),
        "active_agent": "user", "next_action": "", "tool_rounds": 0,
    }

    async def stream():
        final_messages = None
        try:
            async with asyncio.timeout(settings.CHAT_TIMEOUT_SECONDS):
                events = request.app.state.graph.astream_events(initial_state, version="v2", config={"recursion_limit": 40})
                async for event in cancellable_events(events, lambda: store.is_active(session_id, lease)):
                    kind, name = event.get("event"), event.get("name")
                    data = event.get("data", {})
                    if kind == "on_chain_start" and name in {"supervisor", "tool_agent", "responder"}:
                        yield sse("agent_state", {"active_agent": name})
                    elif kind == "on_tool_start":
                        yield sse("tool_call", {"tool": name, "input": data.get("input")})
                    elif kind == "on_tool_end":
                        yield sse("tool_result", {"tool": name, "output": str(data.get("output"))[:20000]})
                    elif kind == "on_chat_model_stream" and event.get("metadata", {}).get("langgraph_node") == "responder":
                        chunk = data.get("chunk")
                        token = text_content(chunk.content) if chunk else ""
                        if token:
                            yield sse("token", {"token": token})
                    elif kind == "on_chain_end" and name == "LangGraph" and not event.get("parent_ids"):
                        final_messages = data.get("output", {}).get("messages")
            if not final_messages:
                if not await asyncio.to_thread(store.is_active, session_id, lease):
                    return
                raise RuntimeError("Graph did not return a final conversation")
            await asyncio.to_thread(store.finish, session_id, lease, final_messages)
            yield sse("done", {"session_id": session_id})
        except TimeoutError:
            yield sse("error", {"detail": "The response timed out. Please try again."})
        except Exception:
            logger.exception("Chat failed for session %s", session_id)
            yield sse("error", {"detail": "Unable to complete the response. Please try again."})
        finally:
            # Failed and cancelled turns never commit partial conversation history.
            await asyncio.shield(asyncio.to_thread(store.finish, session_id, lease))

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no",
    })


@router.post("/api/sessions/{session_id}/cancel", status_code=204)
async def cancel_response(session_id: str, payload: CancelRequest, request: Request, owner: str = Depends(session_owner)):
    await asyncio.to_thread(request.app.state.sessions.cancel, session_id, owner, str(payload.request_id))
    return Response(status_code=204)
