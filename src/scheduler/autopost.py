# autoposter — bg task that wakes up on a schedule and drops posts
# no direct bot or userbot dep — just two injected callbacks keep it clean

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from src.ai.llm import LLMEngine

log = logging.getLogger(__name__)


class AutoPoster:
    # generates posts on a timer and fires publish + notify callbacks
    # set_interval cancels the current loop and starts a fresh one — no state leaks

    def __init__(
        self,
        llm: LLMEngine,
        publish_fn: Callable[[str], Awaitable[None]],
        notify_fn:  Callable[[str], Awaitable[None]],
    ) -> None:
        self._llm        = llm
        self._publish_fn = publish_fn
        self._notify_fn  = notify_fn

        self._interval_hours: float              = 0.0
        self._task:           Optional[asyncio.Task] = None

    @property
    def interval_hours(self) -> float:
        # current interval — 0 means the poster is dead
        return self._interval_hours

    def set_interval(self, hours: float) -> None:
        # change interval mid-run — kills current loop and spawns new one
        self._interval_hours = hours
        self._restart()

    def start(self, initial_hours: float) -> None:
        # called once at startup with the default interval from settings
        self._interval_hours = initial_hours
        self._restart()

    def _restart(self) -> None:
        # cancel whatever is running then start fresh if interval > 0
        if self._task and not self._task.done():
            self._task.cancel()
        if self._interval_hours > 0:
            self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        # sleeps for the interval then generates and publishes — loops forever until cancelled
        log.info('autoposter started: every %.1f h', self._interval_hours)
        while True:
            await asyncio.sleep(self._interval_hours * 3600)
            try:
                post = await asyncio.get_event_loop().run_in_executor(
                    None, self._llm.generate_post, ''
                )
                if not post:
                    continue

                await self._publish_fn(post)
                await self._notify_fn(post)
                log.info('auto-post published -> %s…', post[:60])

            except asyncio.CancelledError:
                log.info('autoposter stopped')
                return
            except Exception as e:
                log.error('autoposter error -> %s', e)
                # try to dm the owner about the failure — best effort
                err_type = type(e).__name__
                try:
                    await self._notify_fn(f'auto-poster error\n\n{err_type}  {e}')
                except Exception:
                    pass
