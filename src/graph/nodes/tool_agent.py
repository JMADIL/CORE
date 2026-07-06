import os
import logging
from langchain_core.messages import AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.config import settings
from src.graph.state import AgentState

logger = logging.getLogger("tool_agent")

# Setup server configurations
def get_mcp_server_configs() -> dict:
    configs = {}
    env = os.environ.copy()
    
    # Prepend fnm node bin and uv bin to PATH so sub-processes can run node/uv/uvx
    node_dir = "/home/ajamoun/.local/share/fnm/node-versions/v24.18.0/installation/bin"
    uv_dir = "/home/ajamoun/.local/bin"
    env["PATH"] = f"{node_dir}:{uv_dir}:{env.get('PATH', '')}"
    
    # 1. Weather server (credential-free)
    configs["weather"] = {
        "transport": "stdio",
        "command": f"{node_dir}/npx",
        "args": ["-y", "@h1deya/mcp-server-weather"],
        "env": env
    }
    
    # 2. Time server (credential-free)
    configs["time"] = {
        "transport": "stdio",
        "command": f"{uv_dir}/uvx",
        "args": ["mcp-server-time"],
        "env": env
    }
    
    # 3. Research MCP (credential-free)
    configs["research"] = {
        "transport": "stdio",
        "command": f"{node_dir}/npx",
        "args": ["-y", "researchmcp", "arxiv"],
        "env": env
    }
    
    # 4. Google Maps server (requires key)
    if settings.GOOGLE_MAPS_API_KEY and settings.GOOGLE_MAPS_API_KEY != "placeholder":
        maps_env = env.copy()
        maps_env["GOOGLE_MAPS_API_KEY"] = settings.GOOGLE_MAPS_API_KEY
        configs["google-maps"] = {
            "transport": "stdio",
            "command": f"{node_dir}/npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": maps_env
        }
        
    # 5. Puppeteer server — disabled (crashes on startup without Chrome)
    # configs["puppeteer"] = {
    #     "transport": "stdio",
    #     "command": f"{node_dir}/npx",
    #     "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
    #     "env": env
    # }
    
    # 6. Sequential Thinking server (credential-free)
    configs["sequential-thinking"] = {
        "transport": "stdio",
        "command": f"{node_dir}/npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": env
    }
    
    # 7. MiniMax server (requires key and host)
    if settings.MINIMAX_API_KEY and settings.MINIMAX_API_KEY != "placeholder" and settings.MINIMAX_API_HOST:
        minimax_env = env.copy()
        minimax_env["MINIMAX_API_KEY"] = settings.MINIMAX_API_KEY
        minimax_env["MINIMAX_API_HOST"] = settings.MINIMAX_API_HOST
        configs["minimax"] = {
            "transport": "stdio",
            "command": f"{uv_dir}/uvx",
            "args": ["minimax-mcp"],
            "env": minimax_env
        }
        
    return configs

async def tool_agent_node(state: AgentState) -> dict:
    """
    Tool agent node that discovers tools from external MCP servers,
    invokes the LLM to get tool calls, executes them, and returns results.
    """
    # 1. Instantiate the LLM
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "placeholder":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0.0,
            max_tokens=1000
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = settings.LLM_MODEL
        if "/" in model_name or "gemini" not in model_name.lower():
            model_name = "gemini-2.0-flash"
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0
        )
        
    # 2. Get active MCP server configurations
    server_configs = get_mcp_server_configs()
    
    if not server_configs:
        return {
            "messages": [AIMessage(content="[Tool Agent] No tools configured or available.")],
            "active_agent": "tool_agent"
        }
        
    # 3. Connect to MCP client and get tools
    client = MultiServerMCPClient(server_configs)
    try:
        tools = await client.get_tools()
        
        # Mutate tool names to replace dashes with underscores for Gemini compatibility
        for tool in tools:
            if "-" in tool.name:
                original_name = tool.name
                mutated_name = original_name.replace("-", "_")
                tool.name = mutated_name
                logger.info(f"Renamed tool '{original_name}' to '{mutated_name}' for Gemini compatibility")
                
        tool_names = [tool.name for tool in tools]
        logger.info(f"Discovered {len(tools)} tools from MCP servers: {tool_names}")
        
        if not tools:
            return {
                "messages": [AIMessage(content="[Tool Agent] Connected but no tools were discovered.")],
                "active_agent": "tool_agent"
            }
            
        # 4. Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)
        
        # 5. Prepend system instruction to guide coordinate estimation for weather tools
        from langchain_core.messages import SystemMessage
        system_instruction = SystemMessage(content=(
            "You are a helpful tool-calling assistant. When using weather tools like 'get_forecast' "
            "or 'get_alerts' which require latitude and longitude, if the user specifies a city name "
            "(e.g., 'Chicago', 'Tokyo', 'Paris') without coordinates, use your internal knowledge "
            "to estimate the latitude and longitude of that city and call the tool using those coordinates."
        ))
        
        # Call LLM with instructions and message history
        response = await llm_with_tools.ainvoke([system_instruction] + state["messages"])
        
        new_messages = [response]
        
        # 6. Execute tool calls if any
        if response.tool_calls:
            # Convert tools to a map for easy lookup by name
            tools_map = {tool.name: tool for tool in tools}
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                logger.info(f"Executing tool: {tool_name}")
                if tool_name in tools_map:
                    tool = tools_map[tool_name]
                    try:
                        tool_output = await tool.ainvoke(tool_call["args"])
                        new_messages.append(ToolMessage(
                            content=str(tool_output),
                            name=tool_name,
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_name}: {e}")
                        new_messages.append(ToolMessage(
                            content=f"Error executing tool: {str(e)}",
                            name=tool_name,
                            tool_call_id=tool_call["id"],
                            status="error"
                        ))
                else:
                    new_messages.append(ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found.",
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                        status="error"
                    ))
        else:
            # If LLM didn't call any tools, add a fallback message
            logger.warning("LLM did not produce any tool_calls despite being routed to tool_agent")
            new_messages.append(AIMessage(content="[Tool Agent] Checked tools but decided no action was required."))
    finally:
        # Clean up MCP server subprocess connections
        for server_name in list(server_configs.keys()):
            try:
                if hasattr(client, '_sessions') and server_name in client._sessions:
                    await client._sessions[server_name].__aexit__(None, None, None)
            except Exception:
                pass
            
    # Return updated fields
    return {
        "messages": new_messages,
        "active_agent": "tool_agent"
    }
