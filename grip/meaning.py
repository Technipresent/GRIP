"""Meaning check: two non-generative checkers judge each claim-evidence pair in parallel. Both must agree."""
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Checker(Protocol):
    name: str

    async def score(self, claim: str, passage: str) -> float: ...


class PairVerdict(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class Thresholds:
    support: float = 0.8
    contradict: float = 0.2


@dataclass(frozen=True)
class Score:
    checker: str
    value: float | None


@dataclass(frozen=True)
class PairResult:
    verdict: PairVerdict
    scores: tuple[Score, ...]
    errors: tuple[str, ...] = ()


async def check_pair(claim: str, passage: str, checkers: list, thresholds: Thresholds) -> PairResult:
    if len(checkers) < 2:
        raise ValueError("meaning check requires two independent checkers")
    raw = await asyncio.gather(*(c.score(claim, passage) for c in checkers), return_exceptions=True)
    scores, errors = [], []
    for c, r in zip(checkers, raw):
        if isinstance(r, BaseException):
            errors.append(c.name)
            scores.append(Score(c.name, None))
        else:
            scores.append(Score(c.name, round(float(r), 4)))
    if errors:
        return PairResult(PairVerdict.UNCERTAIN, tuple(scores), tuple(errors))
    values = [s.value for s in scores]
    if all(v >= thresholds.support for v in values):
        verdict = PairVerdict.SUPPORTS
    elif all(v <= thresholds.contradict for v in values):
        verdict = PairVerdict.CONTRADICTS
    else:
        verdict = PairVerdict.UNCERTAIN
    return PairResult(verdict, tuple(scores))
