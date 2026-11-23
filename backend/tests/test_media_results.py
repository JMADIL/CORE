import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from core.config import settings
from core.integrations.media_results import complete_media_run
from core.integrations.shared_media import remember_results
from core.storage.sessions import SessionStore


class MediaResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_generation_is_polled_to_completion_with_owner_checks(self):
        initial = {'flow_id': 'flow-one', 'session_ids': ['run-one'], 'url': 'https://elevenlabs.io/app/flows/one'}
        completed = {'all_completed': True, 'generations': [{'status': 'completed', 'content_url': 'https://files.elevenlabsusercontent.com/image.png'}]}
        poll = AsyncMock(side_effect=[json.dumps({'all_completed': False, 'poll_after_seconds': .25}), json.dumps(completed)])
        generate = AsyncMock()
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', True), patch('core.integrations.media_results.asyncio.sleep', AsyncMock()):
            store = SessionStore(str(Path(folder) / 'db.sqlite'))
            remember_results(json.dumps(initial), 'visitor', store)
            tools = {'elevenlabs_creative_get_flow_run_status': SimpleNamespace(ainvoke=poll), 'elevenlabs_creative_generate_image': SimpleNamespace(ainvoke=generate)}
            result = json.loads(await complete_media_run(json.dumps(initial), tools, 'visitor', store))
            self.assertTrue(result['all_completed'])
            self.assertEqual(result['generations'], completed['generations'])
            self.assertEqual(poll.await_count, 2)
            self.assertEqual(poll.await_args.args[0]['session_ids'], ['run-one'])
            generate.assert_not_called()
            poll.reset_mock()
            await complete_media_run(json.dumps(initial), tools, 'other-visitor', store)
            poll.assert_not_called()

    async def test_pending_and_failed_runs_do_not_start_paid_retries(self):
        initial = json.dumps({'flow_id': 'flow', 'session_ids': ['run']})
        poll = AsyncMock(return_value=json.dumps({'has_failures': True}))
        tools = {'elevenlabs_creative_get_flow_run_status': SimpleNamespace(ainvoke=poll)}
        with patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', False):
            result = json.loads(await complete_media_run(initial, tools, 'visitor', None))
            self.assertTrue(result['has_failures'])
            poll.assert_awaited_once()
            poll.reset_mock()
            self.assertEqual(json.loads(await complete_media_run(initial, tools, 'visitor', None, wait_seconds=0)), json.loads(initial))
            poll.assert_not_called()

    async def test_status_outage_preserves_the_existing_run(self):
        initial = json.dumps({'flow_id': 'flow', 'session_ids': ['run']})
        tools = {'elevenlabs_creative_get_flow_run_status': SimpleNamespace(ainvoke=AsyncMock(side_effect=TimeoutError()))}
        with patch.object(settings, 'ELEVENLABS_SHARED_ACCOUNT', False):
            self.assertEqual(json.loads(await complete_media_run(initial, tools, 'visitor', None)), json.loads(initial))
