"""Run against a disposable database with TEST_POSTGRES_URL set."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from core.config import settings
from core.storage.errors import SessionAccessDenied, SessionBusy, RateLimitExceeded
from core.storage.postgres import PostgresSessionStore


@unittest.skipUnless(os.getenv("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL to a disposable PostgreSQL database")
class PostgresTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ["TEST_POSTGRES_URL"]
        self.store = PostgresSessionStore(self.url)
        # This suite is deliberately opt-in: it owns the test database tables.
        with self.store.connect() as db:
            db.execute("TRUNCATE sessions, requests, media_requests, media_resources")

    def test_history_survives_new_store_instance(self):
        lease, history = self.store.claim("one", "owner", "client")
        self.assertEqual(history, [])
        self.store.finish("one", lease, [HumanMessage(content="hello"), AIMessage(content="hi")])
        other = PostgresSessionStore(self.url)
        _, history = other.claim("one", "owner", "client")
        self.assertEqual([message.content for message in history], ["hello", "hi"])

    def test_shared_generation_limit_is_atomic_across_instances(self):
        def reserve(index):
            try:
                PostgresSessionStore(self.url).reserve_media(f"visitor-{index}")
                return True
            except RateLimitExceeded:
                return False
        with patch.object(settings, "ELEVENLABS_DEMO_GLOBAL", 2):
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(reserve, range(6)))
        self.assertEqual(sum(results), 2)
        self.store.remember_media_resource("flow:mine", "owner")
        other = PostgresSessionStore(self.url)
        other.check_media_resource("flow:mine", "owner")
        with self.assertRaises(SessionAccessDenied):
            other.check_media_resource("flow:mine", "different-visitor")

    def test_speech_cap_is_independent_and_atomic_across_instances(self):
        def reserve(index):
            try:
                PostgresSessionStore(self.url).reserve_media(f'visitor-{index}', kind='speech')
                return True
            except RateLimitExceeded:
                return False
        with patch.object(settings, 'ELEVENLABS_DEMO_GLOBAL', 1), patch.object(settings, 'ELEVENLABS_TTS_DEMO_GLOBAL', 2):
            self.store.reserve_media('visitor-0')
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(reserve, range(6)))
            self.assertEqual(sum(results), 2)
            with self.assertRaisesRegex(RateLimitExceeded, 'media generation attempts'):
                self.store.reserve_media('another-visitor')

    def test_concurrent_claims_have_one_winner(self):
        def claim(_):
            try:
                return PostgresSessionStore(self.url).claim("parallel", "owner", "client")[0]
            except SessionBusy:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(claim, range(4)))
        self.assertEqual(sum(value is not None for value in results), 1)

    def test_cancel_is_visible_to_other_instances_and_preserves_next_turn(self):
        old, _ = self.store.claim("cancel", "owner", "client", "first-request")
        other = PostgresSessionStore(self.url)
        other.cancel("cancel", "owner", "first-request")
        self.assertFalse(self.store.is_active("cancel", old))
        new, history = other.claim("cancel", "owner", "client", "second-request")
        self.assertEqual(history, [])
        self.store.cancel("cancel", "owner", "first-request")
        self.store.finish("cancel", old, [HumanMessage(content="stale"), AIMessage(content="stale")])
        self.assertTrue(other.is_active("cancel", new))

    def test_ownership_delete_and_cancelled_turn(self):
        lease, _ = self.store.claim("one", "owner", "client")
        self.store.finish("one", lease, [HumanMessage(content="hello"), AIMessage(content="hi")])
        with self.assertRaises(SessionAccessDenied):
            self.store.claim("one", "other", "client")
        lease, _ = self.store.claim("one", "owner", "client")
        with self.assertRaises(SessionBusy):
            self.store.delete("one", "owner")
        self.store.finish("one", lease)
        with self.assertRaises(SessionAccessDenied):
            self.store.delete("one", "other")
        self.store.delete("one", "owner")
        _, history = self.store.claim("one", "new-owner", "client")
        self.assertEqual(history, [])

    def test_rate_limit_transaction_rolls_back(self):
        with patch.object(settings, "REQUESTS_PER_MINUTE", 1):
            lease, _ = self.store.claim("one", "owner", "client")
            self.store.finish("one", lease)
            with self.assertRaises(RateLimitExceeded):
                self.store.claim("two", "owner", "client")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("two",)).fetchone()[0], 0)

    def test_stale_lease_cannot_release_replacement(self):
        old, _ = self.store.claim("one", "owner", "client")
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET updated = 0, busy_until = 0 WHERE id = ?", ("one",))
        replacement, _ = self.store.claim("one", "new-owner", "client")
        self.store.finish("one", old)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT lease FROM sessions WHERE id = ?", ("one",)).fetchone()[0], replacement)

    def test_global_rate_limit_is_atomic_across_instances(self):
        def claim(index):
            try:
                return PostgresSessionStore(self.url).claim(f"turn-{index}", "owner", f"client-{index}")[0]
            except RateLimitExceeded:
                return None
        with patch.object(settings, "GLOBAL_REQUESTS_PER_MINUTE", 1), ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(claim, range(4)))
        self.assertEqual(sum(value is not None for value in results), 1)

    def test_streamed_api_saves_postgres_conversation(self):
        import importlib
        from fastapi.testclient import TestClient
        from langchain_core.messages import AIMessageChunk
        api = importlib.import_module("core.main")

        class Graph:
            async def astream_events(self, state, **kwargs):
                yield {"event": "on_chat_model_stream", "metadata": {"langgraph_node": "responder"},
                       "data": {"chunk": AIMessageChunk(content="Hello from PostgreSQL")}}
                yield {"event": "on_chain_end", "name": "LangGraph", "parent_ids": [],
                       "data": {"output": {"messages": state["messages"] + [AIMessage(content="Hello from PostgreSQL")]}}}

        token = "a" * 64
        with patch.object(api, "create_session_store", return_value=self.store), patch.object(api, "build_graph", return_value=Graph()), patch.object(settings, "CHAT_API_KEY", ""), TestClient(api.app) as client:
            response = client.post("/backend/api/chat", headers={"X-Client-Token": token}, json={"message": "hello", "session_id": "stream"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: token", response.text)
        self.assertIn("event: done", response.text)
        with self.store.connect() as db:
            row = db.execute("SELECT messages FROM sessions WHERE id = ?", ("stream",)).fetchone()
        self.assertIn("Hello from PostgreSQL", row[0])
