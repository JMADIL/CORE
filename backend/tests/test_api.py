"""Deterministic API regressions; no external models or MCP servers required."""
import asyncio
import importlib
import hashlib
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, AsyncMock
import httpx
from openai import RateLimitError

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk

from core.storage.sessions import SessionStore
from core.config import settings
from core.api.dependencies import session_owner
from core.api.routes import chat_endpoint
from core.api.schemas import ChatRequest

api = importlib.import_module("core.main")
TOKEN = "a" * 64
HEADERS = {"X-Client-Token": TOKEN}


class FakeGraph:
    def __init__(self):
        self.states = []
        self.fail = False
        self.failure = None

    async def astream_events(self, state, **kwargs):
        self.states.append(state)
        yield {"event": "on_chain_start", "name": "responder"}
        if self.failure:
            raise self.failure
        if self.fail:
            raise RuntimeError("private provider credential details")
        yield {"event": "on_chat_model_stream", "metadata": {"langgraph_node": "responder"},
               "data": {"chunk": AIMessageChunk(content=[{"type": "text", "text": "Hello"}])}}
        yield {"event": "on_chain_end", "name": "LangGraph", "parent_ids": [],
               "data": {"output": {"messages": state["messages"] + [AIMessage(content="Hello")]}}}


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.graph = FakeGraph()
        self.patches = [patch.object(settings, "DATABASE_PATH", str(Path(self.temp.name) / "sessions.db")),
                        patch.object(settings, "DATABASE_URL", ""),
                        patch.object(settings, "ELEVENLABS_CONNECTOR", ""),
                        patch.object(settings, "ELEVENLABS_SHARED_ACCOUNT", False),
                        patch.object(settings, "CORE_PUBLIC_URL", ""),
                        patch.object(settings, "CHAT_API_KEY", ""), patch.object(settings, "REQUESTS_PER_MINUTE", 30),
                        patch.object(api, "build_graph", return_value=self.graph)]
        for item in self.patches:
            item.start()
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def chat(self, message="hello", session="test", headers=None):
        return self.client.post("/api/chat", json={"message": message, "session_id": session}, headers=headers or HEADERS)

    def test_health_and_stream(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        response = self.chat()
        self.assertEqual(response.status_code, 200)
        self.assertIn('event: token\ndata: {"token": "Hello"}', response.text)
        self.assertIn("event: done", response.text)
        self.assertIn('"content": "Hello"', response.text)

    def test_completed_answer_is_delivered_when_provider_emits_no_tokens(self):
        async def events(state, **kwargs):
            yield {'event': 'on_chain_start', 'name': 'responder'}
            yield {'event': 'on_chain_end', 'name': 'LangGraph', 'parent_ids': [],
                   'data': {'output': {'messages': state['messages'] + [AIMessage(content='Your image is still generating.')]}}}
        with patch.object(self.graph, 'astream_events', side_effect=events):
            response = self.chat()
        self.assertNotIn('event: token', response.text)
        self.assertIn('event: done', response.text)
        self.assertIn('"content": "Your image is still generating."', response.text)

    def test_empty_final_answer_is_an_error_instead_of_empty_success(self):
        async def events(state, **kwargs):
            yield {'event': 'on_chain_end', 'name': 'LangGraph', 'parent_ids': [],
                   'data': {'output': {'messages': state['messages'] + [AIMessage(content='')]}}}
        with patch.object(self.graph, 'astream_events', side_effect=events):
            response = self.chat()
        self.assertIn('event: error', response.text)
        self.assertNotIn('event: done', response.text)

    def test_vercel_service_paths_share_api_and_ownership(self):
        self.assertEqual(self.client.get("/backend/health").status_code, 200)
        response = self.client.post("/backend/api/chat", json={"message": "hello", "session_id": "service-path"}, headers=HEADERS)
        self.assertIn("event: token", response.text)
        self.assertIn("event: done", response.text)
        self.assertEqual(self.client.delete("/backend/api/sessions/service-path", headers={"X-Client-Token": "b" * 64}).status_code, 403)
        self.assertEqual(self.client.delete("/backend/api/sessions/service-path", headers=HEADERS).status_code, 204)

    def test_explicit_cancel_checks_owner_and_request_id(self):
        request_id = "c13665ec-2042-4218-8f45-5bca565ebd43"
        owner = session_owner(TOKEN, "")
        old, _ = api.app.state.sessions.claim("stop", owner, "local", request_id)
        response = self.client.post("/backend/api/sessions/stop/cancel", headers={"X-Client-Token": "b" * 64}, json={"request_id": request_id})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(api.app.state.sessions.is_active("stop", old))
        response = self.client.post("/backend/api/sessions/stop/cancel", headers=HEADERS, json={"request_id": "bad"})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/backend/api/sessions/stop/cancel", headers=HEADERS, json={"request_id": request_id})
        self.assertEqual(response.status_code, 204)
        self.assertFalse(api.app.state.sessions.is_active("stop", old))
        self.assertEqual(self.chat("continue", session="stop").status_code, 200)

    def test_history_survives_store_recreation(self):
        self.chat("first")
        api.app.state.sessions = SessionStore(settings.DATABASE_PATH)
        self.chat("second")
        self.assertEqual([m.content for m in self.graph.states[-1]["messages"]], ["first", "Hello", "second"])

    def test_ownership(self):
        self.chat()
        other = {"X-Client-Token": "b" * 64}
        self.assertEqual(self.chat(headers=other).status_code, 403)
        self.assertEqual(self.client.delete("/api/sessions/test", headers=other).status_code, 403)
        self.assertEqual(self.client.delete("/api/sessions/test", headers=HEADERS).status_code, 204)

    def test_optional_api_key(self):
        with patch.object(settings, "CHAT_API_KEY", "secret"):
            self.assertEqual(self.chat().status_code, 401)
            self.assertEqual(self.chat(headers={**HEADERS, "X-API-Key": "secret"}).status_code, 200)

    def test_validation(self):
        for message in ["", "   ", "x" * 12001]:
            self.assertEqual(self.chat(message).status_code, 422)
        self.assertEqual(self.chat(session="../bad").status_code, 422)
        self.assertEqual(self.client.post("/api/chat", json={"message": "hello"}).status_code, 422)

    def test_body_limit_including_chunked_upload(self):
        with patch.object(settings, "MAX_REQUEST_BYTES", 100):
            response = self.client.post("/api/chat", content=iter([b"x" * 60, b"y" * 60]), headers=HEADERS)
        self.assertEqual(response.status_code, 413)

    def test_real_graph_streams_and_saves_final_history(self):
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        from core.graph.builder import build_graph
        model = FakeListChatModel(responses=["Hello from graph"])
        with patch("core.graph.nodes.responder.create_llm", return_value=model), patch.object(api.app.state, "graph", build_graph()):
            response = self.chat()
        self.assertIn("event: token", response.text)
        self.assertIn("event: done", response.text)
        self.chat("next")
        self.assertEqual(self.graph.states[-1]["messages"][1].content, "Hello from graph")

    def test_cancelled_stream_releases_session_and_rolls_back(self):
        from starlette.requests import Request
        async def cancel():
            request = Request({"type": "http", "app": api.app, "client": ("local", 1234)})
            response = await chat_endpoint(ChatRequest(message="cancel me", session_id="cancel"), request, session_owner(TOKEN, ""))
            await anext(response.body_iterator)
            await response.body_iterator.aclose()
            store = api.app.state.sessions
            lease, history = await asyncio.to_thread(store.claim, "cancel", session_owner(TOKEN, ""), "local")
            self.assertEqual(history, [])
            await asyncio.to_thread(store.finish, "cancel", lease)
        asyncio.run(cancel())

    def test_failure_rolls_back_and_sanitizes_error(self):
        self.chat("first")
        self.graph.fail = True
        with self.assertLogs("api", level="ERROR"):
            response = self.chat("failed")
        self.assertIn("event: error", response.text)
        self.assertNotIn("private provider", response.text)
        self.graph.fail = False
        self.chat("retry")
        self.assertEqual([m.content for m in self.graph.states[-1]["messages"]], ["first", "Hello", "retry"])

    def test_rate_limit(self):
        with patch.object(settings, "REQUESTS_PER_MINUTE", 1):
            self.assertEqual(self.chat().status_code, 200)
            response = self.chat()
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers["retry-after"], "60")

    def test_elevenlabs_image_daily_limit_has_direct_notice_and_chat_can_continue(self):
        from core.integrations.elevenlabs import ElevenLabsImageLimit
        with patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', True):
            self.graph.failure = ElevenLabsImageLimit()
            response = self.chat('Generate a banana image')
        self.assertIn('"code": "elevenlabs_image_daily_limit"', response.text)
        self.assertIn('shared ElevenLabs account', response.text)
        self.assertIn('daily image generation limit', response.text)
        self.assertNotIn('event: done', response.text)
        self.graph.failure = None
        self.assertIn('event: done', self.chat('hello').text)

    def test_model_daily_limit_is_explained_and_session_can_continue(self):
        self.chat("first")
        self.graph.failure = RateLimitError(
            "private provider response",
            response=httpx.Response(429, request=httpx.Request("POST", "https://provider.example/chat")),
            body={"error": {"message": "Rate limit exceeded: free-models-per-day",
                            "metadata": {"limit_source": "openrouter_free_tier_daily"}}},
        )
        with self.assertLogs("api", level="ERROR"):
            response = self.chat("limited")
        self.assertIn('"code": "model_daily_limit"', response.text)
        self.assertIn("daily usage limit", response.text)
        self.assertNotIn("private provider", response.text)
        self.assertNotIn("event: done", response.text)
        self.graph.failure = None
        self.assertIn("event: done", self.chat("retry").text)
        self.assertEqual([m.content for m in self.graph.states[-1]["messages"]], ["first", "Hello", "retry"])

    def test_model_temporary_limit_does_not_claim_daily_quota(self):
        self.graph.failure = RateLimitError(
            "private provider response",
            response=httpx.Response(429, request=httpx.Request("POST", "https://provider.example/chat")),
            body={"message": "Too many requests", "metadata": None},
        )
        with self.assertLogs("api", level="ERROR"):
            response = self.chat()
        self.assertIn('"code": "model_rate_limit"', response.text)
        self.assertIn("request limit", response.text)
        self.assertNotIn("daily", response.text)
        self.assertNotIn("private provider", response.text)

    def test_capacity(self):
        with patch.object(settings, "MAX_SESSIONS", 1):
            self.chat()
            self.assertEqual(self.chat(session="second").status_code, 503)

    def test_busy_session_is_rejected(self):
        self.chat()
        store = api.app.state.sessions
        lease, _ = store.claim("test", session_owner(TOKEN, ""), "local")
        try:
            self.assertEqual(self.chat().status_code, 409)
            self.assertEqual(self.client.delete("/api/sessions/test", headers=HEADERS).status_code, 409)
        finally:
            store.finish("test", lease)
        self.assertEqual(self.chat().status_code, 200)

    def test_request_timeout(self):
        class SlowGraph:
            async def astream_events(self, *args, **kwargs):
                await asyncio.sleep(10)
                yield {}
        with patch.object(api.app.state, "graph", SlowGraph()), patch.object(settings, "CHAT_TIMEOUT_SECONDS", 0.01):
            response = self.chat()
        self.assertIn("timed out", response.text)
        self.assertEqual(self.chat().status_code, 200)

    def test_history_limit_keeps_whole_turns(self):
        with patch.object(settings, "MAX_HISTORY_TURNS", 2):
            self.chat("one")
            self.chat("two")
            self.chat("three")
            self.assertEqual([m.content for m in self.graph.states[-1]["messages"]], ["two", "Hello", "three"])

    def test_cors_rejects_unlisted_origin(self):
        response = self.client.options("/api/chat", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        self.assertEqual(response.status_code, 400)

    def test_elevenlabs_connection_hides_credentials_and_requires_owner(self):
        from core.api import elevenlabs as routes
        path = "/backend/api/integrations/elevenlabs"
        self.assertEqual(self.client.get(path).status_code, 422)
        self.assertEqual(self.client.get(path, headers=HEADERS).json(), {"enabled": False, "connected": False, "mode": "personal"})
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(settings, "CORE_PUBLIC_URL", "https://core.example"), patch.object(routes.elevenlabs, "provider_token", AsyncMock(return_value="private-token")) as token:
            response = self.client.get(path, headers=HEADERS)
        self.assertEqual(response.json(), {"enabled": True, "connected": True, "mode": "personal"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(token.await_args.args, (session_owner(TOKEN, ""),))

    def test_monkey_image_request_explains_missing_connection_without_calling_model(self):
        from core.graph.builder import build_graph
        from core.integrations.elevenlabs import ElevenLabsUnavailable
        from core.graph.nodes import tool_agent, responder
        with patch.object(api.app.state, "graph", build_graph()), patch.object(tool_agent, "discover_tools", AsyncMock(side_effect=ElevenLabsUnavailable(connection_required=True))) as discover, patch.object(tool_agent, "create_llm") as planner, patch.object(responder, "create_llm") as writer:
            response = self.chat("can you generate for me an image for a monkey", session="monkey")
        self.assertIn('"code": "elevenlabs_connection_required"', response.text)
        self.assertIn("Open ElevenLabs in the sidebar", response.text)
        self.assertNotIn("event: done", response.text)
        planner.assert_not_called()
        writer.assert_not_called()
        discover.assert_awaited_once_with(session_owner(TOKEN, ""), require_elevenlabs=True)
        self.assertIn("event: done", self.chat("hello", session="monkey").text)

    def test_vercel_sdk_headers_follow_only_the_current_request(self):
        from core.api import elevenlabs as routes
        from vercel.headers import get_headers
        observed = []
        async def token(*args, **kwargs):
            observed.append(get_headers().get("x-vercel-oidc-token"))
            return "provider-token"
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(settings, "CORE_PUBLIC_URL", "https://core.example"), patch.object(routes.elevenlabs, "provider_token", side_effect=token):
            self.assertEqual(self.client.get("/backend/api/integrations/elevenlabs", headers={**HEADERS, "x-vercel-oidc-token": "platform-request-token"}).status_code, 200)
            self.assertEqual(self.client.get("/backend/api/integrations/elevenlabs", headers=HEADERS).status_code, 200)
        self.assertEqual(observed, ["platform-request-token", None])

    def test_visitors_cannot_replace_or_disconnect_shared_account(self):
        from core.api import elevenlabs as routes
        path = "/backend/api/integrations/elevenlabs"
        with patch.object(settings, "ELEVENLABS_SHARED_ACCOUNT", True), patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/shared"), patch.object(settings, "CORE_PUBLIC_URL", "https://core.example"), patch.object(routes.connect, "start_authorization", AsyncMock()) as start, patch.object(routes.connect, "revoke_token", AsyncMock()) as revoke, patch.object(routes.elevenlabs, "provider_token", AsyncMock(return_value="secret")):
            self.assertEqual(self.client.post(path + "/connect", headers=HEADERS).status_code, 403)
            self.assertEqual(self.client.delete(path, headers=HEADERS).status_code, 403)
            self.assertEqual(self.client.get(path, headers=HEADERS).json(), {"enabled": True, "connected": True, "mode": "shared"})
        start.assert_not_called()
        revoke.assert_not_called()

    def test_shared_owner_setup_requires_private_key_and_uses_runtime_authority(self):
        from core.api import elevenlabs as routes
        key = 'test-owner-setup-key'
        path = '/backend/api/integrations/elevenlabs/owner-connect'
        result = SimpleNamespace(url='https://connect.vercel.com/authorize/test', device_code='TEST-CODE')
        with patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', True), patch.object(settings, 'ELEVENLABS_CONNECTOR', 'oauth/shared'), patch.object(settings, 'CORE_PUBLIC_URL', 'https://core.example'), patch.object(settings, 'ELEVENLABS_OWNER_SETUP_HASH', hashlib.sha256(key.encode()).hexdigest()), patch.object(routes.elevenlabs, 'options', return_value=None), patch.object(routes.connect, 'start_authorization', AsyncMock(return_value=result)) as start:
            for headers in [HEADERS, {**HEADERS, 'X-Core-Setup-Key': 'wrong'}]:
                self.assertEqual(self.client.post(path, headers=headers).status_code, 403)
            start.assert_not_called()
            response = self.client.post(path, headers={'X-Core-Setup-Key': key}, json={'subject': 'attacker'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertEqual(response.json(), {'url': result.url, 'device_code': result.device_code})
            self.assertEqual(start.await_args.kwargs['subject'].id, routes.elevenlabs.SHARED_SUBJECT)
            self.assertTrue(start.await_args.kwargs['device_code'])
            with patch.object(settings, 'ELEVENLABS_OWNER_SETUP_HASH', ''):
                self.assertEqual(self.client.post(path, headers={'X-Core-Setup-Key': key}).status_code, 404)

    def test_elevenlabs_authorization_uses_configured_return_url_and_disconnects_owner_only(self):
        from core.api import elevenlabs as routes
        path = "/backend/api/integrations/elevenlabs"
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(settings, "CORE_PUBLIC_URL", "https://core.example"), patch.object(routes.elevenlabs, "options", return_value=None), patch.object(routes.connect, "start_authorization", AsyncMock(return_value=SimpleNamespace(url="https://vercel.com/authorize/example"))) as start, patch.object(routes.connect, "revoke_token", AsyncMock()) as revoke:
            response = self.client.post(path + "/connect", headers=HEADERS, json={"return_url": "https://attacker.example"})
            self.assertEqual(response.json(), {"url": "https://vercel.com/authorize/example"})
            self.assertEqual(start.await_args.kwargs["return_url"], "https://core.example/")
            self.assertEqual(start.await_args.kwargs["subject"].id, session_owner(TOKEN, ""))
            self.assertEqual(self.client.delete(path, headers=HEADERS).status_code, 204)
            self.assertEqual(revoke.await_args.kwargs["subject"].id, session_owner(TOKEN, ""))
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(settings, "CORE_PUBLIC_URL", "http://attacker.example"):
            self.assertEqual(self.client.post(path + "/connect", headers=HEADERS).status_code, 503)


if __name__ == "__main__":
    unittest.main()
