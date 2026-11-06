from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.config import Settings
from app.domain import ContestClass, ContestType, classify_contest


class ScrapeError(RuntimeError):
    pass


class UserNotFoundError(ScrapeError):
    pass


@dataclass(frozen=True, slots=True)
class ScrapedContest:
    contest_id: str
    name: str
    contest_class: ContestClass
    contest_type: ContestType
    start_at: datetime
    duration_minutes: int | None
    rated_range_min: int | None
    rated_range_max: int | None
    rated_range_display: str | None
    url: str


@dataclass(frozen=True, slots=True)
class ScrapedParticipation:
    contest: ScrapedContest
    rank: int | None
    performance: int | None
    new_rating: int | None
    rating_change: int | None


def _parse_datetime(value: str) -> datetime:
    cleaned = value.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
        except ValueError:
            continue
    raise ScrapeError(f"Unsupported datetime: {value!r}")


def _optional_int(value: str) -> int | None:
    cleaned = value.strip().replace(",", "").replace("+", "")
    if not cleaned or cleaned == "-":
        return None
    match = re.search(r"-?\d+", cleaned)
    return int(match.group()) if match else None


def _duration_minutes(value: str) -> int | None:
    match = re.fullmatch(r"\s*(\d+):(\d{2})\s*", value)
    return int(match.group(1)) * 60 + int(match.group(2)) if match else None


def _rated_range(value: str) -> tuple[int | None, int | None, str | None]:
    display = value.strip()
    if not display or display == "-":
        return None, None, display or None
    if display.lower() == "all":
        return None, None, display
    numbers = [int(number) for number in re.findall(r"\d+", display)]
    if not numbers:
        return None, None, display
    if display.lstrip().startswith("-"):
        return None, numbers[0], display
    if display.rstrip().endswith("-"):
        return numbers[0], None, display
    return numbers[0], numbers[1] if len(numbers) > 1 else numbers[0], display


def _contest_link(row: Tag) -> Tag | None:
    return row.find("a", href=re.compile(r"^/contests/[^/?#]+$"))


def parse_archive_page(html: str, base_url: str) -> tuple[list[ScrapedContest], set[int]]:
    soup = BeautifulSoup(html, "html.parser")
    contests: list[ScrapedContest] = []
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td", recursive=False)
        link = _contest_link(row)
        if len(cells) < 4 or link is None:
            continue
        href = str(link.get("href", ""))
        contest_id = href.split("/")[2]
        name = link.get_text(" ", strip=True)
        contest_class = classify_contest(name)
        marker = cells[1].get_text(" ", strip=True)
        contest_type = (
            ContestType.HEURISTIC
            if contest_class == ContestClass.AHC or "Ⓗ" in marker
            else ContestType.ALGORITHM
        )
        time_tag = cells[0].find("time")
        start_text = time_tag.get_text(strip=True) if time_tag else cells[0].get_text(strip=True)
        rated_min, rated_max, rated_display = _rated_range(cells[3].get_text(" ", strip=True))
        contests.append(
            ScrapedContest(
                contest_id=contest_id,
                name=name,
                contest_class=contest_class,
                contest_type=contest_type,
                start_at=_parse_datetime(start_text),
                duration_minutes=_duration_minutes(cells[2].get_text(strip=True)),
                rated_range_min=rated_min,
                rated_range_max=rated_max,
                rated_range_display=rated_display,
                url=urljoin(base_url, href),
            )
        )
    pages = {
        int(match.group(1))
        for anchor in soup.select("a[href]")
        if (match := re.search(r"[?&]page=(\d+)", str(anchor.get("href"))))
    }
    return contests, pages


def parse_history_page(
    html: str, base_url: str, contest_type: ContestType
) -> list[ScrapedParticipation]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if title and "404" in title.get_text():
        raise UserNotFoundError("AtCoder user was not found")
    table = soup.select_one("table#history")
    if table is None:
        raise ScrapeError("History table was not found")

    results: list[ScrapedParticipation] = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        link = _contest_link(row)
        if len(cells) < 6 or link is None:
            continue
        href = str(link.get("href", ""))
        contest_id = href.split("/")[2]
        name = link.get_text(" ", strip=True)
        order = str(cells[0].get("data-order", ""))
        time_tag = cells[0].find("time")
        date_text = time_tag.get_text(strip=True) if time_tag else order
        contest_class = classify_contest(name)
        results.append(
            ScrapedParticipation(
                contest=ScrapedContest(
                    contest_id=contest_id,
                    name=name,
                    contest_class=contest_class,
                    contest_type=contest_type,
                    start_at=_parse_datetime(date_text),
                    duration_minutes=None,
                    rated_range_min=None,
                    rated_range_max=None,
                    rated_range_display=None,
                    url=urljoin(base_url, href),
                ),
                rank=_optional_int(cells[2].get_text(strip=True)),
                performance=_optional_int(cells[3].get_text(strip=True)),
                new_rating=_optional_int(cells[4].get_text(strip=True)),
                rating_change=_optional_int(cells[5].get_text(strip=True)),
            )
        )
    return results


class AtCoderClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.atcoder_base_url,
            headers={"User-Agent": settings.atcoder_user_agent, "Accept-Language": "en"},
            timeout=settings.http_timeout_seconds,
            follow_redirects=True,
        )
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def __aenter__(self) -> AtCoderClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, str | int] | None = None) -> str:
        async with self._request_lock:
            loop = asyncio.get_running_loop()
            wait = self._settings.http_request_interval_seconds - (
                loop.time() - self._last_request_at
            )
            if wait > 0:
                await asyncio.sleep(wait)
            for attempt in range(self._settings.http_max_retries):
                try:
                    response = await self._client.get(path, params=params)
                    self._last_request_at = loop.time()
                    if response.status_code == 404:
                        raise UserNotFoundError(f"Resource not found: {path}")
                    response.raise_for_status()
                    return response.text
                except UserNotFoundError:
                    raise
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    if attempt + 1 == self._settings.http_max_retries:
                        raise ScrapeError(f"Failed to fetch {path}: {exc}") from exc
                    await asyncio.sleep(2**attempt)
            raise AssertionError("unreachable")

    async def fetch_archive(self) -> list[ScrapedContest]:
        first_html = await self._get("/contests/archive", {"lang": "en"})
        contests, pages = parse_archive_page(first_html, self._settings.atcoder_base_url)
        for page in range(2, max(pages, default=1) + 1):
            html = await self._get("/contests/archive", {"lang": "en", "page": page})
            page_contests, _ = parse_archive_page(html, self._settings.atcoder_base_url)
            contests.extend(page_contests)
        return contests

    async def fetch_user_history(self, username: str) -> list[ScrapedParticipation]:
        all_results: list[ScrapedParticipation] = []
        for query_value, contest_type in (
            ("algo", ContestType.ALGORITHM),
            ("heuristic", ContestType.HEURISTIC),
        ):
            html = await self._get(
                f"/users/{username}/history", {"contestType": query_value, "lang": "en"}
            )
            all_results.extend(
                parse_history_page(html, self._settings.atcoder_base_url, contest_type)
            )
        return all_results
