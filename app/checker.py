from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings
from app.domain import ContestClass
from app.scraper import AtCoderClient, ScrapedParticipation


def parse_target_classes(value: str) -> frozenset[ContestClass]:
    values = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not values:
        raise ValueError("TARGET_CONTEST_CLASSES must contain at least one contest class")
    try:
        return frozenset(ContestClass(item) for item in values)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ContestClass)
        raise ValueError(f"TARGET_CONTEST_CLASSES must be selected from: {allowed}") from exc


def qualifying_participations(
    participations: list[ScrapedParticipation],
    target_classes: frozenset[ContestClass],
    checked_at: datetime,
) -> list[ScrapedParticipation]:
    end = checked_at.astimezone(UTC)
    start = end - timedelta(days=7)
    return [
        item
        for item in participations
        if item.contest.contest_class in target_classes
        and start <= item.contest.start_at < end
    ]


async def send_webhook(url: str, payload: dict[str, object], timeout: float) -> None:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def check_and_notify(
    settings: Settings,
    *,
    checked_at: datetime | None = None,
) -> bool:
    now = checked_at or datetime.now(UTC)
    target_classes = parse_target_classes(settings.target_contest_classes)
    async with AtCoderClient(settings) as client:
        history = await client.fetch_user_history(settings.atcoder_username)

    matches = qualifying_participations(history, target_classes, now)
    if matches:
        return False

    payload: dict[str, object] = {
        "value1": settings.webhook_value1 or settings.atcoder_username,
        "value2": settings.webhook_value2
        or ",".join(sorted(item.value for item in target_classes)),
        "value3": settings.webhook_value3 or now.astimezone(UTC).isoformat(),
    }
    await send_webhook(settings.warning_webhook_url, payload, settings.http_timeout_seconds)
    await asyncio.sleep(settings.webhook_delay_seconds)
    await send_webhook(settings.penalty_webhook_url, payload, settings.http_timeout_seconds)
    return True
