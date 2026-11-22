"""Application composition and the single ASGI entry point: core.main:app."""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.errors import session_error_response
from core.api.limits import ChatBodyLimit
from core.api.routes import router
from core.config import settings
from core.graph.builder import build_graph
from core.storage.errors import SessionError
from core.storage.factory import create_session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.sessions = await asyncio.to_thread(create_session_store)
    app.state.graph = build_graph()
    yield


app = FastAPI(title="Multi-Agent Chatbot Core API", version="0.1.0", lifespan=lifespan)
app.add_middleware(ChatBodyLimit)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Client-Token", "X-API-Key"],
)
app.add_exception_handler(SessionError, session_error_response)
app.include_router(router)
# Vercel Services forwards the original /backend/... request path. Local Next.js
# rewrites strip that prefix, so retain both paths with the same dependencies.
app.include_router(router, prefix="/backend", include_in_schema=False)


def run():
    """Start the installed core-api command."""
    import uvicorn
    uvicorn.run("core.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    run()
