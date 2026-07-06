from langchain_core.messages import HumanMessage, ToolMessage
from src.config import settings
from src.graph.state import AgentState

async def supervisor_node(state: AgentState) -> dict:
    """
    Supervisor coordinator node that inspects the state history and decides
    whether to route to 'tool_agent' (for tools) or 'responder' (for direct answering).
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "active_agent": "supervisor",
            "next_action": "responder"
        }

    # 1. Find the last HumanMessage (not ToolMessage or AIMessage)
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break

    if last_human_idx == -1:
        return {
            "active_agent": "supervisor",
            "next_action": "responder"
        }

    last_human_msg = messages[last_human_idx].content.lower().strip()

    # 2. Check if tool execution has already occurred in the current turn (messages after last HumanMessage)
    has_tool_run = False
    for msg in messages[last_human_idx + 1:]:
        # Check if message is a ToolMessage
        if isinstance(msg, ToolMessage) or (hasattr(msg, "type") and msg.type == "tool"):
            has_tool_run = True
            break
        # Check if it's our placeholder/fallback agent message
        if hasattr(msg, "content") and any(phrase in msg.content for phrase in ["[Tool Agent]", "No tools configured"]):
            has_tool_run = True
            break

    if has_tool_run:
        # If we have already executed tools in this turn, route to responder to formulate the final answer
        return {
            "active_agent": "supervisor",
            "next_action": "responder"
        }

    # 3. Heuristic check: if query has keywords suggesting tool use, route to tool_agent
    tool_keywords = [
        # Weather
        "weather", "temp", "temperature", "forecast", "rain", "snow", "degree",
        "humid", "wind", "celsius", "fahrenheit", "climate",
        # Time
        "time", "date", "clock", "current time", "timezone", "what time",
        # Research
        "research", "arxiv", "paper", "scientific", "bibliography", "journal",
        "publication", "study", "search for",
        # Maps / Location
        "map", "directions", "route", "navigate", "location", "distance",
        "nearby", "address", "geocode",
        # Web browsing
        "browse", "screenshot", "scrape", "webpage", "website",
        # Sequential thinking
        "think", "reasoning", "step-by-step", "sequence", "analyze",
        "break down", "sequential",
        # Music
        "music", "song", "minimax", "generate audio", "audio"
    ]

    if any(kw in last_human_msg for kw in tool_keywords):
        return {
            "active_agent": "supervisor",
            "next_action": "tool_agent"
        }

    # 4. Default routing action is responder
    return {
        "active_agent": "supervisor",
        "next_action": "responder"
    }

