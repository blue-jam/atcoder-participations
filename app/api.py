from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_session
from app.domain import ContestClass
from app.repository import list_user_contests
from app.schemas import ContestItem, ContestListResponse, HealthResponse
from app.services import all_contest_classes, as_utc

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/health", response_model=HealthResponse)
def health(session: SessionDependency) -> HealthResponse:
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")


@router.get(
    "/api/v1/users/{username}/contests",
    response_model=ContestListResponse,
)
def user_contests(
    username: str,
    session: SessionDependency,
    contest_class: Annotated[list[ContestClass] | None, Query()] = None,
    include_unparticipated: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ContestListResponse:
    selected_classes = list(dict.fromkeys(contest_class or all_contest_classes()))
    user, archive_synced, total, records = list_user_contests(
        session,
        username,
        selected_classes,
        include_unparticipated,
        limit,
        offset,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User is not registered")
    return ContestListResponse(
        username=username,
        contest_classes=selected_classes,
        include_unparticipated=include_unparticipated,
        total=total,
        limit=limit,
        offset=offset,
        user_last_synced_at=as_utc(user.last_synced_at),
        archive_last_synced_at=archive_synced,
        items=[ContestItem.model_validate(record) for record in records],
    )
