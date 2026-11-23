"""Resolve asynchronous creative runs without starting another paid generation."""
import asyncio
import json
import logging
import time

from core.config import settings
from core.integrations.content import text_content
from core.integrations.shared_media import guard_call, remember_results

logger = logging.getLogger("media_results")


async def complete_media_run(output, tools, owner, store, *, wait_seconds=40):
    try:
        initial = json.loads(output)
    except (TypeError, ValueError):
        return output
    if not isinstance(initial, dict) or not initial.get("flow_id") or not initial.get("session_ids"):
        return output
    if initial.get("all_completed") or initial.get("has_failures"):
        return output
    name = "elevenlabs_creative_get_flow_run_status"
    if name not in tools:
        return output
    arguments = {"context": "Wait for the requested media and retrieve its file URLs; do not generate again.",
                 "flow_id": initial["flow_id"], "session_ids": initial["session_ids"]}
    latest = initial
    deadline = time.monotonic() + wait_seconds
    try:
        while time.monotonic() < deadline:
            if settings.ELEVENLABS_SHARED_ACCOUNT:
                arguments = await asyncio.to_thread(guard_call, name, arguments, owner, store)
            async with asyncio.timeout(min(settings.TOOL_TIMEOUT_SECONDS, max(.01, deadline - time.monotonic()))):
                result = await tools[name].ainvoke(arguments)
            status = json.loads(text_content(result) if isinstance(result, (str, list)) else str(result))
            if not isinstance(status, dict):
                break
            latest = {**initial, **status}
            if settings.ELEVENLABS_SHARED_ACCOUNT:
                await asyncio.to_thread(remember_results, json.dumps(latest), owner, store)
            if status.get("all_completed") or status.get("has_failures"):
                break
            delay = status.get("poll_after_seconds", 2)
            delay = min(10, max(.25, float(delay)))
            remaining = deadline - time.monotonic()
            if remaining <= delay:
                break
            await asyncio.sleep(delay)
    except Exception as error:
        # The paid run still exists. Never turn a failed status lookup into a retry.
        logger.info("Media status lookup unavailable (%s)", type(error).__name__)
    return json.dumps(latest, ensure_ascii=False)
