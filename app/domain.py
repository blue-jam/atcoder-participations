import re
import unicodedata
from enum import StrEnum


class ContestClass(StrEnum):
    ABC = "abc"
    ARC = "arc"
    AGC = "agc"
    AHC = "ahc"
    OTHER = "other"


class ContestType(StrEnum):
    ALGORITHM = "algorithm"
    HEURISTIC = "heuristic"


_CLASS_PATTERNS: tuple[tuple[re.Pattern[str], ContestClass], ...] = (
    (re.compile(r"\bAtCoder\s+Beginner\s+Contest\b", re.IGNORECASE), ContestClass.ABC),
    (re.compile(r"\bAtCoder\s+Regular\s+Contest(?:\+\+|--)?\b", re.IGNORECASE), ContestClass.ARC),
    (re.compile(r"\bAtCoder\s+Grand\s+Contest\b", re.IGNORECASE), ContestClass.AGC),
    (re.compile(r"\bAtCoder\s+Heuristic\s+Contest\b", re.IGNORECASE), ContestClass.AHC),
)


def classify_contest(name: str) -> ContestClass:
    normalized = unicodedata.normalize("NFKC", name)
    for pattern, contest_class in _CLASS_PATTERNS:
        if pattern.search(normalized):
            return contest_class
    return ContestClass.OTHER
