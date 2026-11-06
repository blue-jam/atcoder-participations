from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.config import get_settings
from app.scheduler import SyncScheduler


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler = SyncScheduler(settings)
    if settings.enable_scheduler:
        scheduler.start()
    yield
    await scheduler.stop()


def create_app() -> FastAPI:
    application = FastAPI(
        title="AtCoder Participations API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
