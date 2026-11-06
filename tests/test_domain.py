import pytest

from app.domain import ContestClass, classify_contest


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("AtCoder Beginner Contest 400", ContestClass.ABC),
        ("SMBC Contest (AtCoder Beginner Contest 401)", ContestClass.ABC),
        ("AtCoder Regular Contest++ 233", ContestClass.ARC),
        ("AtCoder Regular Contest-- 229", ContestClass.ARC),
        ("AtCoder Grand Contest 078", ContestClass.AGC),
        ("Sponsor\uff08AtCoder Heuristic Contest 070\uff09", ContestClass.AHC),
        ("CODE FESTIVAL 2016 Final", ContestClass.OTHER),
    ],
)
def test_classify_contest(name: str, expected: ContestClass) -> None:
    assert classify_contest(name) == expected
