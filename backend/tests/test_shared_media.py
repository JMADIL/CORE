"""Shared demo uses owner credentials but isolates visitors and caps attempts."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool

from core.config import settings
from core.integrations import elevenlabs
from core.integrations.shared_media import guard_call, remember_results
from core.storage.sessions import SessionStore
from core.storage.errors import RateLimitExceeded, SessionAccessDenied
from core.graph.nodes import tool_agent


class SharedMediaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SessionStore(str(Path(self.temp.name) / 'sessions.sqlite'))
        mode = patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', True)
        mode.start()
        self.addCleanup(mode.stop)

    async def test_all_visitors_use_server_selected_shared_subject(self):
        with patch.object(elevenlabs.connect, 'get_token', AsyncMock(return_value='secret')) as token:
            await elevenlabs.provider_token('visitor-a')
            await elevenlabs.provider_token('visitor-b')
        self.assertEqual([c.kwargs['subject'].id for c in token.await_args_list], [elevenlabs.SHARED_SUBJECT] * 2)
        self.assertNotIn('Connect ElevenLabs', elevenlabs.ElevenLabsUnavailable(connection_required=True).detail)

    async def test_attempt_limits_are_durable_and_expire(self):
        with patch.object(settings, 'ELEVENLABS_DEMO_PER_VISITOR', 1), patch.object(settings, 'ELEVENLABS_DEMO_GLOBAL', 2):
            self.store.reserve_media('a')
            with self.assertRaisesRegex(RateLimitExceeded, "this browser's demo limit of 1"):
                SessionStore(self.store.path).reserve_media('a')
            self.store.reserve_media('b')
            with self.assertRaisesRegex(RateLimitExceeded, "site-wide limit of 2"):
                self.store.reserve_media('c')
            with self.store.connect() as db:
                db.execute('UPDATE media_requests SET at = 0')
            self.store.reserve_media('a')

    async def test_resources_from_another_visitor_or_owner_workspace_are_rejected(self):
        payload = {'flow_id': 'flow-a', 'node_id': 'node-a', 'session_ids': ['run-a'], 'generations': [{'id': 'gen-a'}]}
        remember_results(json.dumps(payload), 'a', self.store)
        self.assertEqual(guard_call('elevenlabs_creative_get_flow_run_status', {'flow_id': 'flow-a', 'session_ids': ['run-a']}, 'a', self.store)['flow_id'], 'flow-a')
        for owner, args in [('b', {'flow_id': 'flow-a'}), ('a', {'flow_id': 'private-owner-flow'}), ('a', {'flow_id': 'flow-a', 'session_ids': ['other-run']})]:
            with self.assertRaises(SessionAccessDenied):
                guard_call('elevenlabs_creative_get_flow_run_status', args, owner, self.store)
        with self.assertRaises(SessionAccessDenied):
            remember_results(json.dumps(payload), 'b', self.store)

    async def test_only_public_voices_are_listed_and_can_be_shared_between_visitors(self):
        for owner in ['a', 'b']:
            args = guard_call('elevenlabs_creative_list_voices', {'context': 'choose a voice', 'voice_category': 'famous'}, owner, self.store)
            self.assertEqual(args['voice_category'], 'professional')
            remember_results(json.dumps({'voices': [{'voice_id': 'public-voice'}]}), owner, self.store)
            guard_call('elevenlabs_creative_generate_speech', {'voice_id': 'public-voice'}, owner, self.store)
        with self.assertRaises(SessionAccessDenied):
            guard_call('elevenlabs_creative_generate_speech', {'voice_id': 'private-voice'}, 'a', self.store)
        with self.assertRaises(SessionAccessDenied):
            guard_call('elevenlabs_creative_get_generations', {}, 'a', self.store)

    async def test_one_variation_and_one_generation_per_turn_are_enforced(self):
        calls = []
        async def generate(prompt: str, generations_count: int = 4) -> str:
            """Generate test media without contacting a provider."""
            calls.append(generations_count)
            return json.dumps({'flow_id': 'new-flow', 'node_id': 'new-node', 'session_ids': ['new-session']})
        tool = StructuredTool.from_function(coroutine=generate, name='elevenlabs_creative_generate_image')
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content='', tool_calls=[
            {'name': tool.name, 'args': {'prompt': 'monkey', 'generations_count': 4}, 'id': 'one'},
            {'name': tool.name, 'args': {'prompt': 'duplicate'}, 'id': 'two'},
        ])
        with patch.object(tool_agent, 'discover_tools', AsyncMock(return_value=[tool])), patch.object(tool_agent, 'create_llm', return_value=model):
            result = await tool_agent.tool_agent_node({'messages': [HumanMessage(content='Generate a monkey image')]}, {'configurable': {'owner': 'a', 'store': self.store}})
        self.assertEqual(calls, [1])
        self.assertEqual(result['messages'][-1].status, 'error')
        self.store.check_media_resource('flow:new-flow', 'a')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM media_requests').fetchone()[0], 1)

    async def test_generation_count_is_forced_without_relying_on_discovered_schema(self):
        for name in ['creative_generate_image', 'creative_edit_image', 'creative_generate_speech', 'creative_generate_in_flow']:
            for count in [None, 2, 4]:
                args = {'generations_count': count} if count is not None else {}
                self.assertEqual(guard_call(name, args, 'a', self.store)['generations_count'], 1)

    async def test_tts_runs_once_even_when_the_planner_repeats_it_in_a_later_round(self):
        self.store.remember_media_resource('voice:a:public-voice', 'a')
        calls = []
        async def speech(text: str, voice_id: str, generations_count: int = 4) -> str:
            """Simulate TTS without spending credits."""
            calls.append(generations_count)
            return json.dumps({'all_completed':True, 'generations':[{'id':'tts-one','content_url':'https://files.elevenlabsusercontent.com/tts.mp3','content_mime_type':'audio/mpeg'}]})
        tool = StructuredTool.from_function(coroutine=speech,name='elevenlabs_creative_generate_speech')
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content='',tool_calls=[{'name':tool.name,'args':{'text':'Core audio test.','voice_id':'public-voice','generations_count':2},'id':'tts-call'}])
        state = {'messages':[HumanMessage(content='TTS: Core audio test.')], 'tool_rounds':0}
        config = {'configurable':{'owner':'a','store':self.store}}
        with patch.object(tool_agent,'discover_tools',AsyncMock(return_value=[tool])), patch.object(tool_agent,'create_llm',return_value=model):
            first = await tool_agent.tool_agent_node(state,config)
            second = await tool_agent.tool_agent_node({'messages':state['messages']+first['messages'],'tool_rounds':1},config)
        self.assertEqual(calls,[1])
        self.assertEqual(second['messages'][-1].status,'error')

    async def test_audio_estimate_does_not_block_the_single_real_generation(self):
        calls = []
        async def generate(estimate_only: bool = False, generations_count: int = 4) -> str:
            """Fake sound-effect estimation and generation."""
            calls.append((estimate_only,generations_count))
            return json.dumps({'all_completed':True})
        tool = StructuredTool.from_function(coroutine=generate,name='elevenlabs_creative_generate_in_flow')
        model = AsyncMock(); model.bind_tools = lambda tools: model
        model.ainvoke.side_effect = [AIMessage(content='',tool_calls=[{'name':tool.name,'args':{'estimate_only':value},'id':ident}]) for value,ident in [(True,'estimate'),(False,'generate')]]
        state={'messages':[HumanMessage(content='Create one short sound effect')],'tool_rounds':0}
        config={'configurable':{'owner':'a','store':self.store}}
        with patch.object(tool_agent,'discover_tools',AsyncMock(return_value=[tool])), patch.object(tool_agent,'create_llm',return_value=model):
            first=await tool_agent.tool_agent_node(state,config)
            await tool_agent.tool_agent_node({'messages':state['messages']+first['messages'],'tool_rounds':1},config)
        self.assertEqual(calls,[(True,1),(False,1)])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM media_requests').fetchone()[0],1)

    async def test_exhausted_demo_never_calls_provider(self):
        async def generate(prompt: str) -> str:
            """Test generation."""
            raise AssertionError('provider must not run')
        tool = StructuredTool.from_function(coroutine=generate, name='elevenlabs_creative_generate_image')
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content='', tool_calls=[{'name': tool.name, 'args': {'prompt': 'monkey'}, 'id': 'one'}])
        with patch.object(settings, 'ELEVENLABS_DEMO_GLOBAL', 1):
            self.store.reserve_media('already-used')
            with patch.object(tool_agent, 'discover_tools', AsyncMock(return_value=[tool])), patch.object(tool_agent, 'create_llm', return_value=model):
                with self.assertRaises(RateLimitExceeded):
                    await tool_agent.tool_agent_node({'messages': [HumanMessage(content='Generate image')]}, {'configurable': {'owner': 'a', 'store': self.store}})

    async def test_provider_daily_image_limit_is_raised_without_retry_or_raw_error(self):
        calls = []
        async def generate(prompt: str) -> str:
            """Simulate the hosted provider limit without a real generation."""
            calls.append(prompt)
            raise ExceptionGroup('MCP tool error', [RuntimeError('{"error":"429: free_tier_image_limit_reached private-account-details"}')])
        tool = StructuredTool.from_function(coroutine=generate, name='elevenlabs_creative_generate_image')
        model = AsyncMock()
        model.bind_tools = lambda tools: model
        model.ainvoke.return_value = AIMessage(content='', tool_calls=[{'name': tool.name, 'args': {'prompt': 'banana'}, 'id': 'one'}])
        with patch.object(tool_agent, 'discover_tools', AsyncMock(return_value=[tool])), patch.object(tool_agent, 'create_llm', return_value=model):
            with self.assertRaises(elevenlabs.ElevenLabsImageLimit) as raised:
                await tool_agent.tool_agent_node({'messages': [HumanMessage(content='Generate a banana image')]}, {'configurable': {'owner': 'a', 'store': self.store}})
        self.assertEqual(calls, ['banana'])
        self.assertIn('daily image generation limit', str(raised.exception))
        self.assertNotIn('private-account-details', str(raised.exception))
        self.assertFalse(elevenlabs.image_limit_reached(RuntimeError('Unrelated tool error')))
