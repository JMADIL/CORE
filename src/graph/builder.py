from langgraph.graph import StateGraph, START, END
from src.graph.state import AgentState
from src.graph.nodes.supervisor import supervisor_node
from src.graph.nodes.tool_agent import tool_agent_node
from src.graph.nodes.responder import responder_node

def route_next(state: AgentState):
    """
    Determine the next node to transition to based on the next_action field.
    """
    next_action = state.get("next_action")
    if next_action == "tool_agent":
        return "tool_agent"
    return "responder"

def build_graph():
    """
    Build and compile the multi-agent orchestration LangGraph.
    """
    # 1. Initialize StateGraph with our custom AgentState
    builder = StateGraph(AgentState)
    
    # 2. Add the supervisor, tool agent, and responder nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("tool_agent", tool_agent_node)
    builder.add_node("responder", responder_node)
    
    # 3. Define the entry point
    builder.add_edge(START, "supervisor")
    
    # 4. Define the conditional routing from the supervisor
    builder.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "tool_agent": "tool_agent",
            "responder": "responder"
        }
    )
    
    # 5. Route tool agent execution back to the supervisor
    builder.add_edge("tool_agent", "supervisor")
    
    # 6. Route responder execution to END
    builder.add_edge("responder", END)
    
    # 7. Compile and return the graph
    return builder.compile()
