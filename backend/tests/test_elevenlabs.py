"""Account isolation and read-only connection checks; no paid API calls."""
import unittest
import os
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.tools import StructuredTool

from core.config import settings
from core.integrations import elevenlabs
from core.integrations.mcp import client as mcp_client
from core.integrations.mcp.config import get_mcp_server_configs


class ElevenLabsTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_uses_sdk_runtime_oidc_resolution(self):
        with patch.dict(os.environ, {"VERCEL": "1"}):
            self.assertIsNone(elevenlabs.options().vercel_token)
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(callable(elevenlabs.options().vercel_token))

    async def test_provider_credentials_are_scoped_to_owner_and_resource(self):
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(elevenlabs.connect, "get_token", AsyncMock(return_value="private-token")) as get_token:
            await elevenlabs.provider_token("owner-one")
            await elevenlabs.provider_token("owner-two")
        self.assertEqual([call.kwargs["subject"].id for call in get_token.await_args_list], ["owner-one", "owner-two"])
        self.assertEqual(get_token.await_args.kwargs["resources"], [elevenlabs.MCP_URL])
        self.assertNotIn("convai_write", get_token.await_args.kwargs["scopes"])

    async def test_refresh_once_after_unauthorized_but_never_retry_rate_limit(self):
        attempts = []
        def handler(request):
            attempts.append(request.headers["Authorization"])
            return httpx.Response(401 if len(attempts) == 1 else 200)
        with patch.object(elevenlabs, "provider_token", AsyncMock(side_effect=["old", "new"])) as token:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler), auth=elevenlabs.ElevenLabsAuth("owner")) as client:
                self.assertEqual((await client.post("https://api.elevenlabs.io/v1/mcp-creative", json={})).status_code, 200)
        self.assertEqual(attempts, ["Bearer old", "Bearer new"])
        self.assertTrue(token.await_args.kwargs["force_refresh"])
        with patch.object(elevenlabs, "provider_token", AsyncMock(return_value="token")) as token:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(429)), auth=elevenlabs.ElevenLabsAuth("owner")) as client:
                self.assertEqual((await client.post("https://api.elevenlabs.io/v1/mcp-creative", json={})).status_code, 429)
        self.assertEqual(token.await_count, 1)

    async def test_remote_tools_are_isolated_and_limited_to_creative_operations(self):
        mcp_client._caches.clear()
        async def noop() -> str:
            """Test tool."""
            return "ok"
        owners = []
        def configs(owner=None):
            if not owner:
                return {"time": {}}
            owners.append(owner)
            return {"elevenlabs": {"auth": elevenlabs.ElevenLabsAuth(owner)}}
        clients = []
        def create_client(config, **kwargs):
            client = AsyncMock()
            async def get_tools(server_name):
                names = ["clock"] if server_name == "time" else ["creative_generate_image", "creative_delete_brand_kit"]
                return [StructuredTool.from_function(coroutine=noop, name=name) for name in names]
            client.get_tools.side_effect = get_tools
            clients.append(config)
            return client
        with patch.object(mcp_client, "get_mcp_server_configs", side_effect=configs), patch.object(mcp_client, "MultiServerMCPClient", side_effect=create_client):
            first = await mcp_client.discover_tools("one")
            second = await mcp_client.discover_tools("two")
        self.assertEqual(owners, ["one", "two"])
        self.assertEqual([t.name for t in first], ["time_clock", "elevenlabs_creative_generate_image"])
        self.assertIsNot(first[-1], second[-1])
        self.assertEqual([c["elevenlabs"]["auth"].owner for c in clients if "elevenlabs" in c], ["one", "two"])
        self.assertEqual(sum("time" in c for c in clients), 1)

    async def test_missing_remote_authorization_preserves_other_tools(self):
        mcp_client._caches.clear()
        def configs(owner=None):
            return {"elevenlabs": {}} if owner else {}
        client = AsyncMock()
        client.get_tools.side_effect = RuntimeError("Authorization required")
        with patch.object(mcp_client, "get_mcp_server_configs", side_effect=configs), patch.object(mcp_client, "MultiServerMCPClient", return_value=client):
            self.assertEqual(await mcp_client.discover_tools("owner"), [])

    async def test_server_is_absent_without_owner_or_configuration(self):
        with patch.object(settings, "ELEVENLABS_CONNECTOR", "oauth/test"), patch.object(settings, "CORE_PUBLIC_URL", "https://core.example"):
            self.assertNotIn("elevenlabs", get_mcp_server_configs())
            config = get_mcp_server_configs("owner")["elevenlabs"]
            self.assertEqual(config["transport"], "streamable_http")
            self.assertEqual(config["url"], elevenlabs.MCP_URL)
            self.assertNotIn("headers", config)
        with patch.object(settings, "ELEVENLABS_CONNECTOR", ""):
            self.assertNotIn("elevenlabs", get_mcp_server_configs("owner"))
