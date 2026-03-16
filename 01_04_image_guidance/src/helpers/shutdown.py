# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler — registers SIGINT/SIGTERM listeners that run an
async cleanup coroutine before exiting.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/shutdown.js

"""

import asyncio
import signal
from typing import Callable


def on_shutdown(cleanup: Callable) -> Callable:
    """Register SIGINT/SIGTERM handlers that call ``cleanup`` before exit.

    Args:
        cleanup: Async callable to run during shutdown.

    Returns:
        The async shutdown handler (can be awaited manually for clean exit).
    """
    shutting_down = False

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\n")
        await cleanup()

    def _sync_handler(signum: int, frame: object) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(handler())

    signal.signal(signal.SIGINT, _sync_handler)
    try:
        # SIGTERM is not available on Windows
        signal.signal(signal.SIGTERM, _sync_handler)
    except (OSError, AttributeError):
        pass

    return handler
