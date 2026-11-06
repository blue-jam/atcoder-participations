import asyncio
from contextlib import suppress

from app.config import Settings
from app.sync import archive_is_due, sync_archive, sync_due_users


class SyncScheduler:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="atcoder-sync-scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            if archive_is_due(self._settings):
                with suppress(Exception):
                    await sync_archive(self._settings)
            await sync_due_users(self._settings)
            await asyncio.sleep(60)
