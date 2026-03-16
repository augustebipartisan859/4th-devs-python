# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler that registers SIGINT/SIGTERM signal handlers
and calls an async cleanup function exactly once.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/shutdown.js

"""

import asyncio
import signal
from typing import Awaitable, Callable


def on_shutdown(
    cleanup: Callable[[], Awaitable[None]]
) -> Callable[[], Awaitable[None]]:
    """Register OS signal handlers that call *cleanup* exactly once.

    A ``shutting_down`` flag prevents double-execution if both SIGINT and
    SIGTERM fire in quick succession.

    Args:
        cleanup: Async function to call when a shutdown signal is received.

    Returns:
        The async handler function — ``app.py`` can ``await`` it directly
        on normal exit to reuse the same cleanup path.
    """
    shutting_down = False

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print()
        await cleanup()

    def _sync_handler(signum: int, frame: object) -> None:
        """Synchronous signal wrapper — schedules the async handler."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(handler())

    signal.signal(signal.SIGINT, _sync_handler)
    signal.signal(signal.SIGTERM, _sync_handler)

    return handler
