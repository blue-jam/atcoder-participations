from app.domain import ContestClass, ContestType
from app.scraper import parse_archive_page, parse_history_page


def test_parse_archive_page() -> None:
    html = """
    <table><tbody><tr>
      <td><time>2026-10-31 21:00:00+0900</time></td>
      <td>Ⓐ◉ <a href="/contests/abc482">AtCoder Beginner Contest 482</a></td>
      <td>01:40</td><td>- 1999</td>
    </tr></tbody></table>
    <a href="/contests/archive?page=2">2</a>
    """
    contests, pages = parse_archive_page(html, "https://atcoder.jp")
    assert pages == {2}
    assert len(contests) == 1
    assert contests[0].contest_class == ContestClass.ABC
    assert contests[0].duration_minutes == 100
    assert contests[0].rated_range_min is None
    assert contests[0].rated_range_max == 1999


def test_parse_history_with_unrated_and_negative_change() -> None:
    html = """
    <html><head><title>history</title></head><body>
    <table id="history"><tbody>
      <tr><td data-order="2025/01/01 22:40:00"><time>2025-01-01 22:40:00+0900</time></td>
      <td><a href="/contests/abc390">AtCoder Beginner Contest 390</a></td>
      <td><a>123</a></td><td>1500</td><td>1400</td><td data-order="-20">-20</td><td></td></tr>
      <tr><td data-order="2025/01/02 22:40:00"><time>2025-01-02 22:40:00+0900</time></td>
      <td><a href="/contests/example">Example Contest</a></td>
      <td>8</td><td>-</td><td>-</td><td>-</td><td></td></tr>
    </tbody></table></body></html>
    """
    results = parse_history_page(html, "https://atcoder.jp", ContestType.ALGORITHM)
    assert results[0].rating_change == -20
    assert results[1].performance is None
    assert results[1].contest.contest_class == ContestClass.OTHER
