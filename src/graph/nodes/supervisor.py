from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings
from src.graph.state import AgentState

# Define the structured routing schema
class Route(BaseModel):
    """
    Routing decision for the next step in the chat orchestration.
    """
    next: Literal["tool_agent", "end"] = Field(
        ...,
        description="Select 'tool_agent' if the query requires external tools (like weather, math, or web search) that have not been run yet. Select 'end' if the query can be answered directly or if the necessary tool results are already in the conversation."
    )

# Prompt template instructing the supervisor how to route the query
SYSTEM_PROMPT = """You are a supervisor coordinator agent in a multi-agent chat system.
Your job is to analyze the conversation history and decide what action to take next.

You have two choices:
1. "tool_agent": Choose this if the user's request requires tools (e.g., retrieving weather information, performing mathematical calculations, or searching the web) AND those tool results have not yet been fetched or are incomplete.
2. "end": Choose this if the request can be answered directly using the existing conversation history, or if all necessary tools have already run and returned their results, allowing the user's query to be fully answered.

Analyze the conversation history carefully:
- If the conversation history already contains the placeholder message "[Tool Agent] No tools available yet.", this means the tool agent has already been invoked but had no tools available. In this case, you MUST route to "end" to prevent an infinite loop.
- If the tool results are already present in the history, do not execute the tool agent again. Route to "end" so the final response can be generated.
"""

async def supervisor_node(state: AgentState) -> dict:
    """
    Supervisor node that inspects the state and routes to either the tool_agent or ends the graph.
    """
    # Use OpenRouter ChatOpenAI if key is configured, otherwise fallback to ChatGoogleGenerativeAI
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "placeholder":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.GEMINI_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0.0,
            max_tokens=1000
        )
    else:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0
        )
    
    # Configure LLM to yield structured Route output
    structured_llm = llm.with_structured_output(Route)
    
    # Build prompt with system instructions and message history
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Run the chain to get the routing decision
    chain = prompt | structured_llm
    decision = await chain.ainvoke({"messages": state["messages"]})
    
    # Return updated fields
    return {
        "active_agent": "supervisor",
        "next_action": decision.next
    }
