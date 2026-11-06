from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.config import Settings
from app.database import SessionLocal
from app.models import SyncState, User
from app.scraper import AtCoderClient
from app.services import (
    as_utc,
    mark_archive_error,
    mark_user_error,
    replace_user_history,
    upsert_archive,
    utc_now,
)


async def sync_archive(settings: Settings) -> int:
    try:
        async with AtCoderClient(settings) as client:
            contests = await client.fetch_archive()
        with SessionLocal.begin() as session:
            upsert_archive(session, contests, utc_now())
        return len(contests)
    except Exception as exc:
        with SessionLocal.begin() as session:
            mark_archive_error(session, str(exc))
        raise


async def sync_user(username: str, settings: Settings) -> int:
    async with AtCoderClient(settings) as client:
        participations = await client.fetch_user_history(username)
    with SessionLocal.begin() as session:
        user = session.get(User, username)
        if user is None:
            raise LookupError(f"User is not registered: {username}")
        replace_user_history(session, user, participations, utc_now(), settings.sync_interval_hours)
    return len(participations)


async def add_user(username: str, settings: Settings) -> int:
    with SessionLocal() as session:
        if session.get(User, username) is not None:
            raise ValueError(f"User is already registered: {username}")

    async with AtCoderClient(settings) as client:
        archive = await client.fetch_archive()
        participations = await client.fetch_user_history(username)

    now = utc_now()
    with SessionLocal.begin() as session:
        user = User(username=username, created_at=now)
        session.add(user)
        upsert_archive(session, archive, now)
        replace_user_history(session, user, participations, now, settings.sync_interval_hours)
    return len(participations)


async def sync_due_users(settings: Settings) -> int:
    now = utc_now()
    with SessionLocal() as session:
        usernames = session.scalars(
            select(User.username).where((User.next_sync_at.is_(None)) | (User.next_sync_at <= now))
        ).all()
    completed = 0
    for username in usernames:
        try:
            await sync_user(username, settings)
            completed += 1
        except Exception as exc:
            with SessionLocal.begin() as session:
                user = session.get(User, username)
                if user is not None:
                    mark_user_error(session, user, str(exc), settings.sync_interval_hours)
    return completed


def archive_is_due(settings: Settings) -> bool:
    with SessionLocal() as session:
        state = session.get(SyncState, "archive")
        last_synced = as_utc(state.last_synced_at) if state else None
    return (
        last_synced is None
        or last_synced + timedelta(hours=settings.sync_interval_hours) <= utc_now()
    )
