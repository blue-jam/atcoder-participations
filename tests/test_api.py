from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.domain import ContestClass, ContestType
from app.main import create_app
from app.models import Base, Contest, Participation, SyncState, User


def _client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime(2025, 1, 1, tzinfo=UTC)
    with factory.begin() as session:
        session.add(User(username="alice", created_at=now, last_synced_at=now))
        session.add(SyncState(key="archive", last_synced_at=now))
        session.add_all(
            [
                Contest(
                    contest_id="abc2",
                    name="AtCoder Beginner Contest 2",
                    contest_class=ContestClass.ABC,
                    contest_type=ContestType.ALGORITHM,
                    start_at=datetime(2025, 2, 1, tzinfo=UTC),
                    duration_minutes=100,
                    rated_range_min=None,
                    rated_range_max=1999,
                    rated_range_display="- 1999",
                    url="https://atcoder.jp/contests/abc2",
                ),
                Contest(
                    contest_id="arc1",
                    name="AtCoder Regular Contest 1",
                    contest_class=ContestClass.ARC,
                    contest_type=ContestType.ALGORITHM,
                    start_at=datetime(2025, 1, 1, tzinfo=UTC),
                    duration_minutes=120,
                    rated_range_min=1200,
                    rated_range_max=2799,
                    rated_range_display="1200 - 2799",
                    url="https://atcoder.jp/contests/arc1",
                ),
                Contest(
                    contest_id="other1",
                    name="Other Contest",
                    contest_class=ContestClass.OTHER,
                    contest_type=ContestType.ALGORITHM,
                    start_at=datetime(2024, 1, 1, tzinfo=UTC),
                    duration_minutes=None,
                    rated_range_min=None,
                    rated_range_max=None,
                    rated_range_display="-",
                    url="https://atcoder.jp/contests/other1",
                ),
            ]
        )
        session.add(
            Participation(
                username="alice",
                contest_id="arc1",
                rank=10,
                performance=1800,
                new_rating=1500,
                rating_change=20,
            )
        )

    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), factory


def test_defaults_to_participated_only() -> None:
    client, _ = _client()
    response = client.get("/api/v1/users/alice/contests")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participated"] is True


def test_multiple_classes_include_unparticipated_and_pagination() -> None:
    client, _ = _client()
    response = client.get(
        "/api/v1/users/alice/contests",
        params=[
            ("contest_class", "abc"),
            ("contest_class", "arc"),
            ("include_unparticipated", "true"),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["contest_id"] for item in body["items"]] == ["abc2", "arc1"]
    assert body["items"][0]["participated"] is False
    assert body["items"][0]["rank"] is None


def test_invalid_class_and_unknown_user() -> None:
    client, _ = _client()
    assert client.get("/api/v1/users/alice/contests?contest_class=bad").status_code == 422
    assert client.get("/api/v1/users/nobody/contests").status_code == 404
