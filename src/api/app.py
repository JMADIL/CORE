import json
import uuid
import logging
from typing import Dict, List, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, BaseMessage

from src.config import settings
from src.graph.builder import build_graph
from src.api.schemas import ChatRequest, HealthResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title="Multi-Agent Chatbot Core API",
    description="FastAPI streaming server orchestrating LangGraph and MCP tools.",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store mapping session_id -> list of BaseMessages
session_store: Dict[str, List[BaseMessage]] = {}

# Compile the LangGraph
graph = build_graph()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Returns the API health status and the configured LLM model.
    """
    return HealthResponse(
        status="ok",
        model=settings.LLM_MODEL
    )

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint streaming LangGraph events and LLM tokens via Server-Sent Events (SSE).
    """
    # 1. Retrieve or generate session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # 2. Retrieve session messages
    if session_id not in session_store:
        session_store[session_id] = []
        
    session_messages = session_store[session_id]
    
    # 3. Append the new user message
    user_message = HumanMessage(content=request.message)
    session_messages.append(user_message)
    
    # Define the initial state for the graph
    initial_state = {
        "messages": session_messages,
        "active_agent": "user",
        "next_action": ""
    }
    
    async def sse_generator() -> AsyncGenerator[str, None]:
        # Track the final messages state to update session store
        final_messages = None
        
        try:
            async for event in graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")
                name = event.get("name")
                
                # A. Node execution / Agent State changes
                if kind == "on_chain_start":
                    if name in ["supervisor", "tool_agent", "responder"]:
                        yield f"event: agent_state\ndata: {json.dumps({'active_agent': name})}\n\n"
                        
                # B. Tool execution calls
                elif kind == "on_tool_start":
                    tool_input = event.get("data", {}).get("input")
                    yield f"event: tool_call\ndata: {json.dumps({'tool': name, 'input': tool_input})}\n\n"
                    
                # C. Tool execution results
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output")
                    # Clean up output format if it contains langchain message objects
                    if isinstance(tool_output, list):
                        tool_output_serialized = []
                        for item in tool_output:
                            if hasattr(item, "text"):
                                tool_output_serialized.append(item.text)
                            elif isinstance(item, dict) and "text" in item:
                                tool_output_serialized.append(item["text"])
                            else:
                                tool_output_serialized.append(str(item))
                        tool_output = "\n".join(tool_output_serialized)
                    else:
                        tool_output = str(tool_output)
                        
                    yield f"event: tool_result\ndata: {json.dumps({'tool': name, 'output': tool_output})}\n\n"
                    
                # D. Token streaming (only from responder node)
                elif kind == "on_chat_model_stream":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    if node_name == "responder":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and chunk.content:
                            yield f"event: token\ndata: {json.dumps({'token': chunk.content})}\n\n"
                            
                # E. Final chain output
                elif kind == "on_chain_end" and name == "LangGraph":
                    output_data = event.get("data", {})
                    if output_data and "output" in output_data:
                        final_messages = output_data["output"].get("messages")
                        
        except Exception as e:
            logger.error(f"Error during graph streaming: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
            return
            
        # 4. Save updated message history back to session store
        if final_messages:
            session_store[session_id] = final_messages
            
        # 5. Signal end of stream
        yield f"event: done\ndata: {json.dumps({'session_id': session_id})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
