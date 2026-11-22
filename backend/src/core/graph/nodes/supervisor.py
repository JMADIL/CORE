"""Context-aware routing with bounded continuation after tool results."""
import re

from langchain_core.messages import HumanMessage

from core.config import settings
from core.graph.state import AgentState

TOOL_QUERY = re.compile(
    r"\b(weather|temp|temperature|forecast|rain|snow|degrees?|humid(?:ity)?|wind|"
    r"celsius|fahrenheit|climate|time|date|clock|timezone|research|arxiv|papers?|scientific|"
    r"bibliography|journal|publications?|search|maps?|directions|route|navigate|location|"
    r"distance|nearby|address|geocode|browse|screenshot|scrape|webpage|website|"
    r"reasoning|step-by-step|sequential|music|song|minimax|audio)\b", re.I,
)
FOLLOW_UP = re.compile(r"^(and\b|what about\b|how about\b|also\b|there\b|now\b|same\b)", re.I)


async def supervisor_node(state: AgentState) -> dict:
    rounds = state.get("tool_rounds", 0)
    if rounds:
        action = "tool_agent" if state.get("next_action") == "tool_agent" and rounds < settings.MAX_TOOL_ROUNDS else "responder"
    else:
        humans = [message for message in state.get("messages", []) if isinstance(message, HumanMessage)]
        query = str(humans[-1].content).strip() if humans else ""
        needs_tools = bool(TOOL_QUERY.search(query))
        if not needs_tools and FOLLOW_UP.search(query):
            # Carry tool intent through a chain of short follow-ups.
            for previous in reversed(humans[:-1]):
                content = str(previous.content).strip()
                if TOOL_QUERY.search(content):
                    needs_tools = True
                    break
                if not FOLLOW_UP.search(content):
                    break
        action = "tool_agent" if needs_tools else "responder"
    return {"active_agent": "supervisor", "next_action": action}
