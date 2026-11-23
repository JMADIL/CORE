"""Durable, bounded sessions with atomic cross-worker request leases."""
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from langchain_core.messages import HumanMessage, messages_from_dict, messages_to_dict

from core.config import settings
from core.storage.history import trim_history
from core.storage.errors import SessionAccessDenied, SessionBusy, RateLimitExceeded, SessionCapacityExceeded


class SessionStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            self.initialize_schema(db)

    @staticmethod
    def initialize_schema(db):
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, messages TEXT NOT NULL DEFAULT '[]',
                updated DOUBLE PRECISION NOT NULL, lease TEXT, busy_until DOUBLE PRECISION NOT NULL DEFAULT 0)""")
        db.execute("CREATE TABLE IF NOT EXISTS requests (client TEXT NOT NULL, at DOUBLE PRECISION NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS requests_at ON requests(at)")
        db.execute("CREATE TABLE IF NOT EXISTS media_requests (owner TEXT NOT NULL, at DOUBLE PRECISION NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS media_requests_at ON media_requests(at)")
        db.execute("CREATE TABLE IF NOT EXISTS media_resources (id TEXT PRIMARY KEY, owner TEXT NOT NULL, updated DOUBLE PRECISION NOT NULL)")

    @staticmethod
    def begin_write(db):
        db.execute("BEGIN IMMEDIATE")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self, session_id: str, owner: str, client: str, request_id: str | None = None):
        now = time.time()
        lease = secrets.token_hex(16)
        if request_id:
            lease += ":" + request_id
        with self.connect() as db:
            self.begin_write(db)
            db.execute("DELETE FROM requests WHERE at < ?", (now - 60,))
            count = db.execute("SELECT COUNT(*) FROM requests WHERE client = ?", (client,)).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            if count >= settings.REQUESTS_PER_MINUTE or total >= settings.GLOBAL_REQUESTS_PER_MINUTE:
                raise RateLimitExceeded("Too many requests. Try again in a minute.")
            db.execute("DELETE FROM sessions WHERE updated < ? AND busy_until < ?", (now - settings.SESSION_TTL_SECONDS, now))
            row = db.execute("SELECT owner, messages, busy_until FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                if not secrets.compare_digest(row[0], owner):
                    raise SessionAccessDenied("Session belongs to a different browser")
                if row[2] > now:
                    raise SessionBusy("This conversation already has a response in progress")
                messages = messages_from_dict(json.loads(row[1]))
            else:
                if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= settings.MAX_SESSIONS:
                    raise SessionCapacityExceeded("Session capacity reached. Try again later.")
                db.execute("INSERT INTO sessions (id, owner, updated) VALUES (?, ?, ?)", (session_id, owner, now))
                messages = []
            db.execute("INSERT INTO requests VALUES (?, ?)", (client, now))
            db.execute("UPDATE sessions SET lease = ?, busy_until = ?, updated = ? WHERE id = ?",
                       (lease, now + settings.CHAT_TIMEOUT_SECONDS + 30, now, session_id))
        return lease, messages

    def is_active(self, session_id: str, lease: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM sessions WHERE id = ? AND lease = ?", (session_id, lease)).fetchone() is not None

    def cancel(self, session_id: str, owner: str, request_id: str):
        with self.connect() as db:
            self.begin_write(db)
            row = db.execute("SELECT owner, lease FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                return
            if not secrets.compare_digest(row[0], owner):
                raise SessionAccessDenied("Session belongs to a different browser")
            # A delayed cancellation must never stop the user's next request.
            if row[1] and row[1].endswith(":" + request_id):
                db.execute("UPDATE sessions SET lease = NULL, busy_until = 0 WHERE id = ? AND lease = ?", (session_id, row[1]))

    def finish(self, session_id: str, lease: str, messages=None):
        with self.connect() as db:
            if messages is None:
                db.execute("UPDATE sessions SET lease = NULL, busy_until = 0 WHERE id = ? AND lease = ?", (session_id, lease))
                db.execute("DELETE FROM sessions WHERE id = ? AND messages = '[]' AND lease IS NULL", (session_id,))
            else:
                retained = trim_history(messages)
                payload = json.dumps(messages_to_dict(retained))
                while len(payload.encode()) > settings.MAX_HISTORY_BYTES:
                    starts = [i for i, message in enumerate(retained) if isinstance(message, HumanMessage)]
                    if len(starts) < 2:
                        raise ValueError("Conversation turn exceeds the storage limit")
                    retained = retained[starts[1]:]
                    payload = json.dumps(messages_to_dict(retained))
                db.execute("UPDATE sessions SET messages = ?, updated = ?, lease = NULL, busy_until = 0 WHERE id = ? AND lease = ?",
                           (payload, time.time(), session_id, lease))

    def delete(self, session_id: str, owner: str):
        with self.connect() as db:
            self.begin_write(db)
            row = db.execute("SELECT owner, busy_until FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                return
            if not secrets.compare_digest(row[0], owner):
                raise SessionAccessDenied("Session belongs to a different browser")
            if row[1] > time.time():
                raise SessionBusy("Wait for the active response before deleting this thread")
            db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def reserve_media(self, owner: str):
        """Count attempts atomically before a paid call, including uncertain failures."""
        now = time.time()
        with self.connect() as db:
            self.begin_write(db)
            db.execute("DELETE FROM media_requests WHERE at < ?", (now - 86400,))
            db.execute("DELETE FROM media_resources WHERE updated < ?", (now - settings.SESSION_TTL_SECONDS,))
            count = db.execute("SELECT COUNT(*) FROM media_requests WHERE owner = ?", (owner,)).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM media_requests").fetchone()[0]
            if count >= settings.ELEVENLABS_DEMO_PER_VISITOR or total >= settings.ELEVENLABS_DEMO_GLOBAL:
                raise RateLimitExceeded("The shared media demo has reached its generation limit. Please try again later.")
            db.execute("INSERT INTO media_requests VALUES (?, ?)", (owner, now))

    def remember_media_resource(self, flow: str, owner: str):
        with self.connect() as db:
            self.begin_write(db)
            row = db.execute("SELECT owner FROM media_resources WHERE id = ?", (flow,)).fetchone()
            if row and row[0] != owner:
                raise SessionAccessDenied("This media belongs to another visitor.")
            if not row:
                db.execute("INSERT INTO media_resources VALUES (?, ?, ?)", (flow, owner, time.time()))

    def check_media_resource(self, flow: str, owner: str):
        with self.connect() as db:
            row = db.execute("SELECT owner FROM media_resources WHERE id = ?", (flow,)).fetchone()
        if not row or row[0] != owner:
            raise SessionAccessDenied("This media belongs to another visitor or is not available in the demo.")
