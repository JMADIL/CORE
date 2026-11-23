"""Context-aware routing with bounded continuation after tool results."""
import re

from langchain_core.messages import HumanMessage, ToolMessage

from core.config import settings
from core.graph.state import AgentState
from core.graph.intents import requests_media

TOOL_QUERY = re.compile(
    r"\b(weather|temp|temperature|forecast|rain|snow|degrees?|humid(?:ity)?|wind|"
    r"celsius|fahrenheit|climate|time|date|clock|timezone|research|arxiv|papers?|scientific|"
    r"bibliography|journal|publications?|search|maps?|directions|route|navigate|location|"
    r"distance|nearby|address|geocode|browse|screenshot|scrape|webpage|website|"
    r"reasoning|step-by-step|sequential|music|song|minimax|audio|elevenlabs|elevencreative|"
    r"voiceover|soundtrack|text-to-speech)\b|"
    r"\b(?:generate|create|make|edit|animate)\b.{0,100}\b(?:image|picture|video|speech|sound effect)s?\b", re.I,
)
FOLLOW_UP = re.compile(r"^(and\b|what about\b|how about\b|also\b|there\b|now\b|same\b)", re.I)


async def supervisor_node(state: AgentState) -> dict:
    rounds = state.get("tool_rounds", 0)
    if rounds:
        action = "tool_agent" if state.get("next_action") == "tool_agent" and rounds < settings.MAX_TOOL_ROUNDS else "responder"
    else:
        humans = [message for message in state.get("messages", []) if isinstance(message, HumanMessage)]
        query = str(humans[-1].content).strip() if humans else ""
        needs_tools = bool(TOOL_QUERY.search(query)) or requests_media(query)
        if not needs_tools and re.search(r"\b(show|check|display|refresh|ready|finished|status|results?)\b", query, re.I):
            # Existing generations are asynchronous. Let follow-ups retrieve them
            # rather than asking the text-only writer to invent a download link.
            needs_tools = any(isinstance(message, ToolMessage) and (message.name or "").startswith("elevenlabs_")
                              for message in state.get("messages", []))
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
