from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain import ContestClass, ContestType


class ContestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ContestListResponse(BaseModel):
    username: str
    contest_classes: list[ContestClass]
    include_unparticipated: bool
    total: int
    limit: int
    offset: int
    user_last_synced_at: datetime | None
    archive_last_synced_at: datetime | None
    items: list[ContestItem]


class HealthResponse(BaseModel):
    status: str
    database: str
