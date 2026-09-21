from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings
from src.graph.state import AgentState

async def responder_node(state: AgentState) -> dict:
    """
    Responder node that generates the final conversational response based on all the message history.
    """
    # 1. Instantiate the LLM
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "placeholder":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0.7,
            max_tokens=1500,
            streaming=True
        )
    else:
        model_name = settings.LLM_MODEL
        if "/" in model_name or "gemini" not in model_name.lower():
            model_name = "gemini-3.6-flash"
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7
        )
        
    # 2. Invoke the LLM in streaming mode so that LangGraph can broadcast on_chat_model_stream events
    response = None
    async for chunk in llm.astream(state["messages"]):
        if response is None:
            response = chunk
        else:
            response += chunk

    if response is None:
        from langchain_core.messages import AIMessage
        response = AIMessage(content="")
    
    # 3. Append the response to the state
    return {
        "messages": [response],
        "active_agent": "responder"
    }
