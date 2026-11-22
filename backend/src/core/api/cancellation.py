"""Cancel graph execution even when a hosting proxy retains the SSE request."""
import asyncio
import contextvars


async def cancellable_events(events, is_active, interval=1.0):
    async def watch_lease():
        while True:
            await asyncio.sleep(interval)
            if not await asyncio.to_thread(is_active):
                return

    watcher = asyncio.create_task(watch_lease())
    # Async generators may retain ContextVar tokens across yields. All pulls
    # and final cleanup must execute in the same context, even across tasks.
    context = contextvars.copy_context()
    pending = None
    try:
        while True:
            pending = asyncio.create_task(anext(events), context=context)
            done, _ = await asyncio.wait({pending, watcher}, return_when=asyncio.FIRST_COMPLETED)
            if watcher in done:
                watcher.result()
                return
            try:
                event = pending.result()
            except StopAsyncIteration:
                return
            yield event
    finally:
        tasks = [task for task in (pending, watcher) if task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.create_task(events.aclose(), context=context)
