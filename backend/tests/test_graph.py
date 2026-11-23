import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from core.config import settings
from core.graph.builder import build_graph
from core.graph.nodes.supervisor import supervisor_node
from core.graph.nodes import tool_agent
from core.graph.nodes import responder


class GraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_writer_receives_results_without_tool_protocol(self):
        captured = []
        class Model:
            async def astream(self, messages):
                captured.extend(messages)
                yield AIMessageChunk(content="Paper A finds that planning improves reliability.")
        messages = [
            HumanMessage(content="Search arXiv for AI agents"),
            AIMessage(content="", tool_calls=[{"name": "research_search_arxiv", "args": {"query": "AI agents"}, "id": "1"}]),
            ToolMessage(content='[{"title":"Paper A","abstract":"Planning improves reliability."}]', tool_call_id="1", name="research_search_arxiv"),
            AIMessage(content="<tool_call>another search</tool_call>"),
        ]
        with patch.object(responder, "create_llm", return_value=Model()):
            result = await responder.responder_node({"messages": messages})
        self.assertEqual(result["messages"][0].content, "Paper A finds that planning improves reliability.")
        self.assertFalse(any(isinstance(message, ToolMessage) for message in captured))
        self.assertFalse(any(getattr(message, "tool_calls", []) for message in captured))
        self.assertIn("Paper A", captured[-1].content)
        self.assertIn("Search arXiv", captured[1].content)
        self.assertNotIn("<tool_call>", "".join(message.content for message in captured))

    async def test_writer_keeps_conversation_but_not_old_tool_protocol(self):
        messages = [HumanMessage(content="first query"),
                    AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "old"}]),
                    ToolMessage(content="old results", tool_call_id="old"),
                    AIMessage(content="Previous summary"), HumanMessage(content="Explain further")]
        prompt = responder.synthesis_messages(messages)
        self.assertEqual([message.content for message in prompt], ["first query", "Previous summary", "Explain further"])

    async def test_writer_reports_missing_tools_without_fabricating_results(self):
        prompt = responder.synthesis_messages([
            HumanMessage(content="Search arXiv"), AIMessage(content="[Tool Agent] Tools unavailable")])
        self.assertIn("No tool results were retrieved", prompt[-1].content)

    async def test_empty_writer_output_is_a_failure(self):
        class EmptyModel:
            async def astream(self, messages):
                yield AIMessageChunk(content="")
        with patch.object(responder, "create_llm", return_value=EmptyModel()):
            with self.assertRaisesRegex(RuntimeError, "no final answer"):
                await responder.responder_node({"messages": [HumanMessage(content="hello")]})

    async def test_mcp_text_blocks_are_unwrapped_before_synthesis(self):
        async def lookup() -> list:
            """Return MCP text blocks."""
            return [{"type": "text", "text": '[{"title":"Paper A"}]'}]
        tool = StructuredTool.from_function(coroutine=lookup, name="research_search_arxiv")
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content="", tool_calls=[{"name": tool.name, "args": {}, "id": "paper"}])
        with patch.object(tool_agent, "discover_tools", AsyncMock(return_value=[tool])), patch.object(tool_agent, "create_llm", return_value=model):
            result = await tool_agent.tool_agent_node({"messages": []})
        self.assertEqual(result["messages"][-1].content, '[{"title":"Paper A"}]')

    async def test_routing_avoids_substring_matches(self):
        for text in ["Hello", "Write a training loop", "Explain datetime objects", "Update my resume"]:
            result = await supervisor_node({"messages": [HumanMessage(content=text)]})
            self.assertEqual(result["next_action"], "responder", text)

    async def test_media_requests_reach_tool_agent(self):
        for text in ["Generate an image of a cat", "Create a video of a beach", "Make a voiceover", "Use ElevenLabs"]:
            result = await supervisor_node({"messages": [HumanMessage(content=text)]})
            self.assertEqual(result["next_action"], "tool_agent", text)

    async def test_show_existing_media_uses_tools_without_a_new_generation_request(self):
        messages = [HumanMessage(content='Generate a monkey image'),
                    ToolMessage(content='{"flow_id":"existing","session_ids":["run"]}', name='elevenlabs_creative_generate_image', tool_call_id='image'),
                    AIMessage(content='Generation started.'), HumanMessage(content='Show me the image')]
        self.assertEqual((await supervisor_node({'messages': messages}))['next_action'], 'tool_agent')
        self.assertEqual((await supervisor_node({'messages': [HumanMessage(content='Show me an example of recursion')]}))['next_action'], 'responder')

    async def test_media_generation_and_prompt_writing_are_distinct(self):
        from core.graph.intents import requests_media
        for query in ["can you generate for me an image for a monkey", "Draw a monkey", "Read this aloud", "Make a sound effect", "Convert this to speech"]:
            self.assertTrue(requests_media(query), query)
        for query in ["Write a prompt for a monkey image", "Generate a detailed prompt for an image", "Explain video compression", "Tell me about monkeys"]:
            self.assertFalse(requests_media(query), query)

    async def test_real_graph_passes_browser_authority_to_discovery(self):
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content="No generation requested")
        async def writer(state):
            return {"messages": [AIMessage(content="Done")]}
        with patch.object(tool_agent, "discover_tools", AsyncMock(return_value=[SimpleNamespace(name="lookup")])) as discover, patch.object(tool_agent, "create_llm", return_value=model), patch("core.graph.builder.responder_node", writer):
            await build_graph().ainvoke({"messages": [HumanMessage(content="List ElevenLabs models")], "tool_rounds": 0}, config={"configurable": {"owner": "browser-owner"}})
        discover.assert_awaited_once_with("browser-owner")

    async def test_contextual_followups(self):
        messages = [HumanMessage(content="Weather in Tokyo?"), AIMessage(content="Sunny"), HumanMessage(content="And in Paris?")]
        result = await supervisor_node({"messages": messages})
        self.assertEqual(result["next_action"], "tool_agent")

    async def test_tool_rounds_bounded(self):
        result = await supervisor_node({"tool_rounds": settings.MAX_TOOL_ROUNDS, "next_action": "tool_agent"})
        self.assertEqual(result["next_action"], "responder")

    async def test_real_graph_allows_dependent_tool_rounds(self):
        calls = []
        async def lookup(place: str) -> str:
            """Find a place."""
            calls.append(place)
            return "result:" + place
        tool = StructuredTool.from_function(coroutine=lookup, name="lookup")
        responses = [
            AIMessage(content="", tool_calls=[{"name": "lookup", "args": {"place": "first"}, "id": "1"}]),
            AIMessage(content="", tool_calls=[{"name": "lookup", "args": {"place": "second"}, "id": "2"}]),
            AIMessage(content="Done"),
        ]
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.side_effect = responses
        async def responder(state):
            return {"messages": [AIMessage(content="Final")], "active_agent": "responder"}
        with patch.object(tool_agent, "discover_tools", AsyncMock(return_value=[tool])), patch.object(tool_agent, "create_llm", return_value=model), patch("core.graph.builder.responder_node", responder):
            result = await build_graph().ainvoke({"messages": [HumanMessage(content="Research places")], "tool_rounds": 0})
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(result["messages"][-1].content, "Final")
        self.assertEqual(result["tool_rounds"], 3)

    async def test_tool_failure_becomes_error_message(self):
        async def broken(place: str) -> str:
            """Fail deliberately."""
            raise RuntimeError("secret remote details")
        tool = StructuredTool.from_function(coroutine=broken, name="broken")
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content="", tool_calls=[{"name": "broken", "args": {"place": "x"}, "id": "1"}])
        with patch.object(tool_agent, "discover_tools", AsyncMock(return_value=[tool])), patch.object(tool_agent, "create_llm", return_value=model), self.assertLogs("tool_agent", level="WARNING"):
            result = await tool_agent.tool_agent_node({"messages": []})
        self.assertIsInstance(result["messages"][-1], ToolMessage)
        self.assertEqual(result["messages"][-1].status, "error")
        self.assertNotIn("secret", result["messages"][-1].content)

    async def test_unavailable_tools_dont_call_model(self):
        with patch.object(tool_agent, "discover_tools", AsyncMock(return_value=[])), patch.object(tool_agent, "create_llm") as create:
            result = await tool_agent.tool_agent_node({"messages": []})
        create.assert_not_called()
        self.assertEqual(result["next_action"], "responder")


if __name__ == "__main__":
    unittest.main()
