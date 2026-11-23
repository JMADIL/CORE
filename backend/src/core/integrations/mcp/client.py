"""Independent MCP discovery, name normalization, and per-loop tool caching."""
import asyncio
import logging
import re
import time
from weakref import WeakKeyDictionary

from langchain_mcp_adapters.client import MultiServerMCPClient
from core.config import settings
from core.integrations.mcp.config import get_mcp_server_configs

logger = logging.getLogger("mcp")
_caches = WeakKeyDictionary()


async def discover_tools(owner: str | None = None):
    if owner:
        # Reuse local tools globally, but rebuild remote tool closures with this
        # browser's authority on every turn (including after disconnect).
        local = await discover_tools()
        remote = get_mcp_server_configs(owner).get("elevenlabs")
        if not remote:
            return local
        try:
            async with asyncio.timeout(settings.DISCOVERY_TIMEOUT_SECONDS):
                group = await MultiServerMCPClient({"elevenlabs": remote}, handle_tool_errors=False).get_tools(server_name="elevenlabs")
            from core.integrations.elevenlabs import CREATIVE_TOOLS
            approved = [tool for tool in group if tool.name in CREATIVE_TOOLS]
            for tool in approved:
                tool.name = "elevenlabs_" + tool.name
            return local + approved
        except Exception:
            # Not signing in must not break existing research/time tools.
            logger.info("ElevenLabs tools unavailable for this browser")
            return local
    loop = asyncio.get_running_loop()
    cache = _caches.setdefault(loop, {"lock": asyncio.Lock(), "until": 0, "tools": []})
    async with cache["lock"]:
        if time.monotonic() < cache["until"]:
            return cache["tools"]
        configs = get_mcp_server_configs()
        client = MultiServerMCPClient(configs, handle_tool_errors=False)

        async def load(name):
            try:
                async with asyncio.timeout(settings.DISCOVERY_TIMEOUT_SECONDS):
                    return await client.get_tools(server_name=name)
            except Exception:
                logger.warning("MCP server %s unavailable", name, exc_info=True)
                return []

        groups = await asyncio.gather(*(load(name) for name in configs))
        tools = []
        for server, group in zip(configs, groups):
            for tool in group:
                # Prefix to avoid collisions; retain adapter's original remote tool mapping.
                tool.name = re.sub(r"[^a-zA-Z0-9_]", "_", f"{server}_{tool.name}")
                if len(tool.name) > 64 or any(existing.name == tool.name for existing in tools):
                    logger.warning("Skipping tool with invalid or duplicate name: %s", tool.name)
                    continue
                tools.append(tool)
        cache["tools"] = tools
        cache["until"] = time.monotonic() + (settings.MCP_CACHE_SECONDS if tools else min(settings.MCP_CACHE_SECONDS, 10))
        return tools
