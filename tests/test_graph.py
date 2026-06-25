import asyncio
import sys
from langchain_core.messages import HumanMessage
from src.config import settings
from src.graph.builder import build_graph

async def run_test(message_content: str):
    print(f"\n--- Testing with message: '{message_content}' ---")
    graph = build_graph()
    
    # Initialize the state
    initial_state = {
        "messages": [HumanMessage(content=message_content)],
        "active_agent": "user",
        "next_action": ""
    }
    
    try:
        result = await graph.ainvoke(initial_state)
        print("Execution successful!")
        print(f"Active Agent: {result.get('active_agent')}")
        print(f"Next Action: {result.get('next_action')}")
        print("Messages in state:")
        for msg in result.get("messages", []):
            print(f"  [{type(msg).__name__}]: {msg.content}")
        return True
    except Exception as e:
        print(f"Error executing graph: {e}", file=sys.stderr)
        return False

async def main():
    print("Initializing Graph Test...")
    
    # Warn user if neither API key is configured
    has_google = settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != "placeholder"
    has_openrouter = settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "placeholder"
    
    if not has_google and not has_openrouter:
        print("\n[WARNING] Neither GOOGLE_API_KEY nor OPENROUTER_API_KEY is configured in your .env file.")
        print("Please configure at least one API key in your .env file.")
        print("Skipping graph invocation to avoid API authentication error.")
        sys.exit(0)

    print("Running test cases...")
    success1 = await run_test("Hello, how are you?")
    await asyncio.sleep(2)
    success2 = await run_test("What is the weather in Tokyo?")
    
    if success1 and success2:
        print("\nAll tests completed successfully!")
    else:
        print("\nSome tests failed.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
