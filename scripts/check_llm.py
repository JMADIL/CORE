"""Optional live provider smoke test; excluded from the offline unittest suite."""
import asyncio

from langchain_core.messages import HumanMessage
from core.integrations.llm import create_llm, model_name


async def main():
    print(f"Testing configured provider/model: {model_name()}")
    result = await create_llm(temperature=0, max_tokens=50).ainvoke([HumanMessage(content="Say hello briefly.")])
    if not result.content:
        raise RuntimeError("Provider returned an empty response")
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
