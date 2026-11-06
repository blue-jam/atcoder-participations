from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.domain import ContestClass, classify_contest
from app.models import Contest, Participation, SyncState, User
from app.scraper import ScrapedContest, ScrapedParticipation


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def random_next_sync(
    now: datetime, interval_hours: int, rng: random.Random | None = None
) -> datetime:
    generator = rng or random.SystemRandom()
    interval = timedelta(hours=interval_hours)
    interval_seconds = int(interval.total_seconds())
    current_window_start = datetime.fromtimestamp(
        int(now.timestamp()) // interval_seconds * interval_seconds,
        tz=UTC,
    )
    return (
        current_window_start + interval + timedelta(seconds=generator.uniform(0, interval_seconds))
    )


def _contest_values(contest: ScrapedContest) -> dict[str, object]:
    return {
        "contest_id": contest.contest_id,
        "name": contest.name,
        "contest_class": contest.contest_class,
        "contest_type": contest.contest_type,
        "start_at": contest.start_at,
        "duration_minutes": contest.duration_minutes,
        "rated_range_min": contest.rated_range_min,
        "rated_range_max": contest.rated_range_max,
        "rated_range_display": contest.rated_range_display,
        "url": contest.url,
    }


def upsert_archive(session: Session, contests: list[ScrapedContest], synced_at: datetime) -> None:
    for contest in contests:
        values = _contest_values(contest)
        statement = sqlite_insert(Contest).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[Contest.contest_id],
            set_={key: getattr(statement.excluded, key) for key in values if key != "contest_id"},
        )
        session.execute(statement)
    state = session.get(SyncState, "archive")
    if state is None:
        session.add(SyncState(key="archive", last_synced_at=synced_at, last_error=None))
    else:
        state.last_synced_at = synced_at
        state.last_error = None


def mark_archive_error(session: Session, error: str) -> None:
    state = session.get(SyncState, "archive")
    if state is None:
        session.add(SyncState(key="archive", last_synced_at=None, last_error=error))
    else:
        state.last_error = error


def replace_user_history(
    session: Session,
    user: User,
    participations: list[ScrapedParticipation],
    synced_at: datetime,
    interval_hours: int,
) -> None:
    for item in participations:
        existing = session.get(Contest, item.contest.contest_id)
        if existing is None:
            session.add(Contest(**_contest_values(item.contest)))
        else:
            existing.name = item.contest.name
            existing.contest_class = item.contest.contest_class
            existing.contest_type = item.contest.contest_type
            existing.url = item.contest.url
    session.flush()
    session.execute(delete(Participation).where(Participation.username == user.username))
    session.add_all(
        Participation(
            username=user.username,
            contest_id=item.contest.contest_id,
            rank=item.rank,
            performance=item.performance,
            new_rating=item.new_rating,
            rating_change=item.rating_change,
        )
        for item in participations
    )
    user.last_synced_at = synced_at
    user.last_sync_error = None
    user.next_sync_at = random_next_sync(synced_at, interval_hours)


def mark_user_error(session: Session, user: User, error: str, interval_hours: int) -> None:
    now = utc_now()
    user.last_sync_error = error
    user.next_sync_at = random_next_sync(now, interval_hours)


def reclassify_contests(session: Session) -> int:
    contests = session.scalars(select(Contest)).all()
    changed = 0
    for contest in contests:
        new_class = classify_contest(contest.name)
        if contest.contest_class != new_class:
            contest.contest_class = new_class
            changed += 1
    return changed


def all_contest_classes() -> list[ContestClass]:
    return list(ContestClass)
