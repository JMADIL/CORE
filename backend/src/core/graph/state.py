from typing import Annotated, NotRequired, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    State representing the agent's conversation history and coordination.
    """
    messages: Annotated[list, add_messages]   # Conversation history
    active_agent: str                          # "supervisor" | "tool_agent"
    next_action: str                           # Routing decision: "tool_agent" | "end"
    tool_rounds: NotRequired[int]
