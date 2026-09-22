import os
import sys
import shutil
import logging
from langchain_core.messages import AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.config import settings
from src.graph.state import AgentState

logger = logging.getLogger("tool_agent")

def get_mcp_server_configs() -> dict:
    """
    Returns stdio configurations for active MCP servers.
    Dynamically locates node, npx, and python executables.
    """
    configs = {}
    env = os.environ.copy()
    
    node_bin = shutil.which("node") or "/home/ajamoun/.nvm/versions/node/v22.23.1/bin/node"
    npx_bin = shutil.which("npx") or "/home/ajamoun/.nvm/versions/node/v22.23.1/bin/npx"
    python_bin = sys.executable
    
    # 1. Weather server
    weather_cached = "/home/ajamoun/.npm/_npx/bfb2db71e8e3f82e/node_modules/.bin/mcp-server-weather"
    if os.path.exists(weather_cached):
        configs["weather"] = {
            "transport": "stdio",
            "command": node_bin,
            "args": [weather_cached],
            "env": env
        }
    elif npx_bin:
        configs["weather"] = {
            "transport": "stdio",
            "command": npx_bin,
            "args": ["-y", "@h1deya/mcp-server-weather"],
            "env": env
        }
    
    # 2. Time server (powered by python mcp_server_time)
    configs["time"] = {
        "transport": "stdio",
        "command": python_bin,
        "args": ["-m", "mcp_server_time"],
        "env": env
    }
    
    # 3. Research MCP
    research_cached = "/home/ajamoun/.npm/_npx/efb9a46ff596f68c/node_modules/.bin/researchmcp"
    if os.path.exists(research_cached):
        configs["research"] = {
            "transport": "stdio",
            "command": node_bin,
            "args": [research_cached, "arxiv"],
            "env": env
        }
    elif npx_bin:
        configs["research"] = {
            "transport": "stdio",
            "command": npx_bin,
            "args": ["-y", "researchmcp", "arxiv"],
            "env": env
        }
    
    # 4. Google Maps server (optional, requires API key)
    if settings.GOOGLE_MAPS_API_KEY and settings.GOOGLE_MAPS_API_KEY != "placeholder" and npx_bin:
        maps_env = env.copy()
        maps_env["GOOGLE_MAPS_API_KEY"] = settings.GOOGLE_MAPS_API_KEY
        configs["google-maps"] = {
            "transport": "stdio",
            "command": npx_bin,
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": maps_env
        }
        
    # 5. Sequential Thinking server
    seq_cached = "/home/ajamoun/.npm/_npx/de2bd410102f5eda/node_modules/.bin/mcp-server-sequential-thinking"
    if os.path.exists(seq_cached):
        configs["sequential-thinking"] = {
            "transport": "stdio",
            "command": node_bin,
            "args": [seq_cached],
            "env": env
        }
    elif npx_bin:
        configs["sequential-thinking"] = {
            "transport": "stdio",
            "command": npx_bin,
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "env": env
        }
        
    # 6. MiniMax server (optional, requires key and host)
    uvx_bin = shutil.which("uvx")
    if settings.MINIMAX_API_KEY and settings.MINIMAX_API_KEY != "placeholder" and settings.MINIMAX_API_HOST and uvx_bin:
        minimax_env = env.copy()
        minimax_env["MINIMAX_API_KEY"] = settings.MINIMAX_API_KEY
        minimax_env["MINIMAX_API_HOST"] = settings.MINIMAX_API_HOST
        configs["minimax"] = {
            "transport": "stdio",
            "command": uvx_bin,
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
    has_openrouter = (
        bool(settings.OPENROUTER_API_KEY)
        and settings.OPENROUTER_API_KEY.lower() not in ["placeholder", "none", ""]
        and settings.OPENROUTER_API_KEY.startswith("sk-or-")
    )
    if has_openrouter:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0.0,
            max_tokens=1000,
            default_headers={"HTTP-Referer": "https://github.com/JMADIL/CORE", "X-Title": "Core Agent"}
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = settings.LLM_MODEL
        if "/" in model_name or "gemini" not in model_name.lower():
            model_name = "gemini-3.6-flash"
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
        
    # Return updated fields
    return {
        "messages": new_messages,
        "active_agent": "tool_agent"
    }

