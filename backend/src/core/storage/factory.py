"""Choose durable deployment storage without changing local SQLite workflows."""
import os

from core.config import settings
from core.storage.sessions import SessionStore


def create_session_store():
    if settings.DATABASE_URL:
        from core.storage.postgres import PostgresSessionStore
        return PostgresSessionStore(settings.DATABASE_URL)
    if os.getenv("VERCEL"):
        raise ValueError("Set DATABASE_URL to a PostgreSQL connection URL on Vercel")
    return SessionStore(settings.DATABASE_PATH)
