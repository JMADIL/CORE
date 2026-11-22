"""PostgreSQL session persistence for Neon and stateless deployments."""
from contextlib import contextmanager

import psycopg

from core.storage.sessions import SessionStore

# A transaction-scoped lock serializes short admission/deletion transactions,
# matching SQLite's BEGIN IMMEDIATE. Never hold it during model or tool calls.
_ADMISSION_LOCK = 398247601


class _Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        # Queries come only from SessionStore; values always remain parameters.
        return self.connection.execute(sql.replace("?", "%s"), parameters)


class PostgresSessionStore(SessionStore):
    def __init__(self, url: str):
        self.url = url
        with self.connect() as db:
            self.begin_write(db)
            self.initialize_schema(db)

    @contextmanager
    def connect(self):
        # Short-lived connections work with Neon's transaction-pooler endpoint.
        # Disable prepared statements so pooled sessions need no session state.
        with psycopg.connect(self.url, connect_timeout=10, prepare_threshold=None) as connection:
            yield _Connection(connection)

    @staticmethod
    def begin_write(db):
        db.execute("SELECT pg_advisory_xact_lock(?)", (_ADMISSION_LOCK,))
