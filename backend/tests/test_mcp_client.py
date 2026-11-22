"""Offline MCP discovery regressions, separate from graph orchestration."""
import unittest
from unittest.mock import AsyncMock, patch
from langchain_core.tools import StructuredTool
from core.integrations.mcp import client as mcp_client


class MCPClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_isolates_failure_and_caches(self):
        mcp_client._caches.clear()
        async def noop() -> str:
            """Test tool."""
            return "ok"
        tool = StructuredTool.from_function(coroutine=noop, name="current-time")
        client = AsyncMock()
        async def get_tools(server_name):
            if server_name == "broken":
                raise RuntimeError("offline")
            return [tool]
        client.get_tools.side_effect = get_tools
        with patch.object(mcp_client, "get_mcp_server_configs", return_value={"time": {}, "broken": {}}), patch.object(mcp_client, "MultiServerMCPClient", return_value=client), self.assertLogs("mcp", level="WARNING"):
            first = await mcp_client.discover_tools()
            second = await mcp_client.discover_tools()
        self.assertEqual(len(first), 1)
        self.assertIs(first, second)
        self.assertEqual(first[0].name, "time_current_time")
        self.assertEqual(client.get_tools.await_count, 2)


if __name__ == "__main__":
    unittest.main()
