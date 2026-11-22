"""Optional local MCP smoke test. Starts installed servers; no model call."""
import asyncio

from core.integrations.mcp.client import discover_tools


async def main():
    tools = await discover_tools()
    print(f"Discovered {len(tools)} tools")
    for tool in tools:
        print(f"  {tool.name}")
    if not tools:
        raise RuntimeError("No MCP servers could be reached")


if __name__ == "__main__":
    asyncio.run(main())
