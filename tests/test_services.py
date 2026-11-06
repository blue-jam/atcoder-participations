import random
from datetime import UTC, datetime, timedelta

from app.services import random_next_sync


def test_random_next_sync_stays_inside_six_hour_window() -> None:
    now = datetime(2025, 1, 1, tzinfo=UTC)
    result = random_next_sync(now, 6, random.Random(42))
    assert now + timedelta(hours=6) <= result <= now + timedelta(hours=12)
