from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app import checker
from app.checker import parse_target_classes, qualifying_participations
from app.config import Settings
from app.domain import ContestClass, ContestType
from app.scraper import ScrapedContest, ScrapedParticipation


def _participation(start_at: datetime, contest_class: ContestClass) -> ScrapedParticipation:
    return ScrapedParticipation(
        contest=ScrapedContest(
            contest_id="contest-1",
            name="Contest",
            contest_class=contest_class,
            contest_type=ContestType.ALGORITHM,
            start_at=start_at,
            duration_minutes=None,
            rated_range_min=None,
            rated_range_max=None,
            rated_range_display=None,
            url="https://atcoder.jp/contests/contest-1",
        ),
        rank=1,
        performance=2000,
        new_rating=1800,
        rating_change=10,
    )


def _settings() -> Settings:
    return Settings(
        warning_webhook_url="https://example.com/warning",
        penalty_webhook_url="https://example.com/penalty",
        atcoder_username="test_user",
        target_contest_classes="abc,arc",
        webhook_value1="custom-1",
        webhook_value2="custom-2",
        webhook_value3="custom-3",
        webhook_delay_seconds=0,
    )


def test_parse_target_classes() -> None:
    assert parse_target_classes(" ABC, arc,abc ") == {
        ContestClass.ABC,
        ContestClass.ARC,
    }
    with pytest.raises(ValueError, match="selected from"):
        parse_target_classes("abc,bad")


def test_qualifying_participations_uses_previous_seven_days() -> None:
    now = datetime(2026, 11, 2, 14, tzinfo=UTC)
    history = [
        _participation(now - timedelta(days=1), ContestClass.ABC),
        _participation(now - timedelta(days=2), ContestClass.AHC),
        _participation(now - timedelta(days=8), ContestClass.ARC),
    ]
    assert qualifying_participations(
        history, frozenset({ContestClass.ABC, ContestClass.ARC}), now
    ) == [history[0]]


async def test_no_webhook_when_participation_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 11, 2, 14, tzinfo=UTC)
    monkeypatch.setattr(
        checker.AtCoderClient,
        "fetch_user_history",
        AsyncMock(return_value=[_participation(now - timedelta(days=1), ContestClass.ABC)]),
    )
    send = AsyncMock()
    monkeypatch.setattr(checker, "send_webhook", send)

    assert await checker.check_and_notify(_settings(), checked_at=now) is False
    send.assert_not_awaited()


async def test_warning_then_penalty_when_no_participation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 11, 2, 14, tzinfo=UTC)
    monkeypatch.setattr(
        checker.AtCoderClient, "fetch_user_history", AsyncMock(return_value=[])
    )
    send = AsyncMock()
    monkeypatch.setattr(checker, "send_webhook", send)
    settings = _settings()

    assert settings.atcoder_username == "test_user"
    assert await checker.check_and_notify(settings, checked_at=now) is True
    assert [call.args[0] for call in send.await_args_list] == [
        "https://example.com/warning",
        "https://example.com/penalty",
    ]
    assert send.await_args_list[0].args[1] == {
        "value1": "custom-1",
        "value2": "custom-2",
        "value3": "custom-3",
    }
