import asyncio
import sys
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph

async def test_standalone_mcp():
    print("\n--- 1. Testing Standalone MCP Tool Discovery ---")
    env = os.environ.copy()
    node_dir = "/home/ajamoun/.local/share/fnm/node-versions/v24.18.0/installation/bin"
    uv_dir = "/home/ajamoun/.local/bin"
    env["PATH"] = f"{node_dir}:{uv_dir}:{env.get('PATH', '')}"
    
    configs = {
        "time": {
            "transport": "stdio",
            "command": "/home/ajamoun/.local/bin/uvx",
            "args": ["mcp-server-time"],
            "env": env
        },
        "weather": {
            "transport": "stdio",
            "command": "/home/ajamoun/.local/share/fnm/node-versions/v24.18.0/installation/bin/npx",
            "args": ["-y", "@h1deya/mcp-server-weather"],
            "env": env
        },
        "puppeteer": {
            "transport": "stdio",
            "command": "/home/ajamoun/.local/share/fnm/node-versions/v24.18.0/installation/bin/npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "env": env
        },
        "sequential-thinking": {
            "transport": "stdio",
            "command": "/home/ajamoun/.local/share/fnm/node-versions/v24.18.0/installation/bin/npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "env": env
        }
    }
    
    client = MultiServerMCPClient(configs)
    tools = await client.get_tools()
    print(f"Successfully discovered {len(tools)} tools:")
    for t in tools:
        print(f"  - {t.name}: {t.description[:65]}...")
    assert len(tools) > 0
    print("Standalone MCP Discovery passed!")

async def test_graph_with_tools():
    print("\n--- 2. Testing LangGraph Integration with MCP Tools ---")
    graph = build_graph()
    
    # Initialize the state with a query requiring the time tool
    initial_state = {
        "messages": [HumanMessage(content="What is the current time in Tokyo?")],
        "active_agent": "user",
        "next_action": ""
    }
    
    print("Invoking graph with query: 'What is the current time in Tokyo?'")
    try:
        # Increase recursion limit to handle potential loop-back
        result = await graph.ainvoke(initial_state, config={"recursion_limit": 10})
        print("\nGraph execution successful!")
        print(f"Active Agent: {result.get('active_agent')}")
        print(f"Next Action: {result.get('next_action')}")
        
        print("\nMessages in history:")
        for m in result["messages"]:
            content_preview = m.content[:100] + "..." if len(str(m.content)) > 100 else m.content
            print(f"  [{type(m).__name__}]: {content_preview}")
            if hasattr(m, "tool_calls") and m.tool_calls:
                print(f"    Tool Calls: {m.tool_calls}")
                
    except Exception as e:
        print(f"Error invoking graph for time: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    print("\nInvoking graph with query: 'What is the weather forecast for Chicago?'")
    try:
        initial_state = {
            "messages": [HumanMessage(content="What is the weather forecast for Chicago?")],
            "active_agent": "user",
            "next_action": ""
        }
        result = await graph.ainvoke(initial_state, config={"recursion_limit": 10})
        print("\nGraph execution successful!")
        print(f"Active Agent: {result.get('active_agent')}")
        print(f"Next Action: {result.get('next_action')}")
        
        print("\nMessages in history:")
        for m in result["messages"]:
            content_preview = m.content[:100] + "..." if len(str(m.content)) > 100 else m.content
            print(f"  [{type(m).__name__}]: {content_preview}")
            if hasattr(m, "tool_calls") and m.tool_calls:
                print(f"    Tool Calls: {m.tool_calls}")
                
    except Exception as e:
        print(f"Error invoking graph for weather: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

async def main():
    await test_standalone_mcp()
    # Add a brief sleep to let system handles clear
    await asyncio.sleep(2)
    await test_graph_with_tools()

if __name__ == "__main__":
    asyncio.run(main())
