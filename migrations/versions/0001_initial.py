"""Initial schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("next_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_error", sa.Text()),
    )
    op.create_index("ix_users_next_sync_at", "users", ["next_sync_at"])
    op.create_table(
        "contests",
        sa.Column("contest_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("contest_class", sa.String(5), nullable=False),
        sa.Column("contest_type", sa.String(9), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("rated_range_min", sa.Integer()),
        sa.Column("rated_range_max", sa.Integer()),
        sa.Column("rated_range_display", sa.String(64)),
        sa.Column("url", sa.Text(), nullable=False),
    )
    op.create_index("ix_contests_start_at", "contests", ["start_at"])
    op.create_index("ix_contests_class_start", "contests", ["contest_class", "start_at"])
    op.create_table(
        "participations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "username",
            sa.String(64),
            sa.ForeignKey("users.username", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contest_id", sa.String(128), sa.ForeignKey("contests.contest_id"), nullable=False
        ),
        sa.Column("rank", sa.Integer()),
        sa.Column("performance", sa.Integer()),
        sa.Column("new_rating", sa.Integer()),
        sa.Column("rating_change", sa.Integer()),
        sa.UniqueConstraint("username", "contest_id"),
    )
    op.create_index("ix_participations_username", "participations", ["username"])
    op.create_index("ix_participations_contest_id", "participations", ["contest_id"])
    op.create_table(
        "sync_states",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("sync_states")
    op.drop_table("participations")
    op.drop_table("contests")
    op.drop_table("users")
