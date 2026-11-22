import asyncio
import contextvars
import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from core.api.cancellation import cancellable_events
from core.storage.errors import SessionAccessDenied
from core.storage.sessions import SessionStore


class CancellationStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SessionStore(str(Path(self.temp.name) / "sessions.db"))

    def test_cancel_releases_only_matching_request_and_rolls_back(self):
        old, _ = self.store.claim("chat", "owner", "client", "request-one")
        with self.assertRaises(SessionAccessDenied):
            self.store.cancel("chat", "other", "request-one")
        self.assertTrue(self.store.is_active("chat", old))
        self.store.cancel("chat", "owner", "request-one")
        self.assertFalse(self.store.is_active("chat", old))
        new, history = self.store.claim("chat", "owner", "client", "request-two")
        self.assertEqual(history, [])
        self.store.cancel("chat", "owner", "request-one")
        self.store.finish("chat", old, [HumanMessage(content="cancelled"), AIMessage(content="late answer")])
        self.assertTrue(self.store.is_active("chat", new))
        self.store.finish("chat", new, [HumanMessage(content="new"), AIMessage(content="current")])
        _, history = self.store.claim("chat", "owner", "client")
        self.assertEqual([message.content for message in history], ["new", "current"])

    def test_cancel_unknown_session_is_idempotent(self):
        self.store.cancel("missing", "owner", "request-one")
        self.store.cancel("missing", "owner", "request-one")


class CancellationStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalidated_lease_stops_blocked_graph_execution(self):
        active = True
        closed = asyncio.Event()

        async def events():
            try:
                yield "started"
                await asyncio.sleep(60)
                yield "should not arrive"
            finally:
                closed.set()

        stream = cancellable_events(events(), lambda: active, interval=0.01)
        self.assertEqual(await anext(stream), "started")
        active = False
        with self.assertRaises(StopAsyncIteration):
            await asyncio.wait_for(anext(stream), timeout=1)
        self.assertTrue(closed.is_set())

    async def test_completed_graph_is_not_cancelled(self):
        async def events():
            yield "token"
            yield "done"
        values = [value async for value in cancellable_events(events(), lambda: True, interval=0.01)]
        self.assertEqual(values, ["token", "done"])

    async def test_graph_context_survives_yields_and_early_close(self):
        current = contextvars.ContextVar("graph_context", default="outside")

        async def events():
            token = current.set("inside")
            try:
                yield current.get()
                yield current.get()
            finally:
                current.reset(token)

        stream = cancellable_events(events(), lambda: True)
        self.assertEqual(await anext(stream), "inside")
        await stream.aclose()
        self.assertEqual(current.get(), "outside")
        self.assertEqual([v async for v in cancellable_events(events(), lambda: True)], ["inside", "inside"])
