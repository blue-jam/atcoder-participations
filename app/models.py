from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain import ContestClass, ContestType


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    participations: Mapped[list["Participation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Contest(Base):
    __tablename__ = "contests"
    __table_args__ = (Index("ix_contests_class_start", "contest_class", "start_at"),)

    contest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    contest_class: Mapped[ContestClass] = mapped_column(
        Enum(
            ContestClass,
            native_enum=False,
            values_callable=lambda values: [v.value for v in values],
        )
    )
    contest_type: Mapped[ContestType] = mapped_column(
        Enum(
            ContestType, native_enum=False, values_callable=lambda values: [v.value for v in values]
        )
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    rated_range_min: Mapped[int | None] = mapped_column(Integer)
    rated_range_max: Mapped[int | None] = mapped_column(Integer)
    rated_range_display: Mapped[str | None] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    participations: Mapped[list["Participation"]] = relationship(back_populates="contest")


class Participation(Base):
    __tablename__ = "participations"
    __table_args__ = (UniqueConstraint("username", "contest_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        ForeignKey("users.username", ondelete="CASCADE"), index=True
    )
    contest_id: Mapped[str] = mapped_column(ForeignKey("contests.contest_id"), index=True)
    rank: Mapped[int | None] = mapped_column(Integer)
    performance: Mapped[int | None] = mapped_column(Integer)
    new_rating: Mapped[int | None] = mapped_column(Integer)
    rating_change: Mapped[int | None] = mapped_column(Integer)
    user: Mapped[User] = relationship(back_populates="participations")
    contest: Mapped[Contest] = relationship(back_populates="participations")


class SyncState(Base):
    __tablename__ = "sync_states"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
