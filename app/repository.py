from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.domain import ContestClass, ContestType
from app.models import Contest, Participation, SyncState, User
from app.services import as_utc


@dataclass(frozen=True, slots=True)
class ContestRecord:
    contest_id: str
    contest_name: str
    contest_class: ContestClass
    contest_type: ContestType
    participated: bool
    start_at: datetime
    duration_minutes: int | None
    rank: int | None
    performance: int | None
    new_rating: int | None
    rating_change: int | None
    rated_range_min: int | None
    rated_range_max: int | None
    rated_range_display: str | None
    contest_url: str


def _base_query(
    username: str, include_unparticipated: bool
) -> Select[tuple[Contest, Participation]]:
    if include_unparticipated:
        return select(Contest, Participation).outerjoin(
            Participation,
            and_(
                Participation.contest_id == Contest.contest_id,
                Participation.username == username,
            ),
        )
    return select(Contest, Participation).join(
        Participation,
        and_(
            Participation.contest_id == Contest.contest_id,
            Participation.username == username,
        ),
    )


def list_user_contests(
    session: Session,
    username: str,
    contest_classes: list[ContestClass],
    include_unparticipated: bool,
    limit: int,
    offset: int,
) -> tuple[User | None, datetime | None, int, list[ContestRecord]]:
    user = session.get(User, username)
    archive_state = session.get(SyncState, "archive")
    if user is None:
        return None, as_utc(archive_state.last_synced_at) if archive_state else None, 0, []

    filtered = _base_query(username, include_unparticipated).where(
        Contest.contest_class.in_(contest_classes)
    )
    total = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    rows = session.execute(
        filtered.order_by(Contest.start_at.desc(), Contest.contest_id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        ContestRecord(
            contest_id=contest.contest_id,
            contest_name=contest.name,
            contest_class=contest.contest_class,
            contest_type=contest.contest_type,
            participated=participation is not None,
            start_at=as_utc(contest.start_at) or contest.start_at,
            duration_minutes=contest.duration_minutes,
            rank=participation.rank if participation else None,
            performance=participation.performance if participation else None,
            new_rating=participation.new_rating if participation else None,
            rating_change=participation.rating_change if participation else None,
            rated_range_min=contest.rated_range_min,
            rated_range_max=contest.rated_range_max,
            rated_range_display=contest.rated_range_display,
            contest_url=contest.url,
        )
        for contest, participation in rows
    ]
    return (
        user,
        as_utc(archive_state.last_synced_at) if archive_state else None,
        total,
        items,
    )
