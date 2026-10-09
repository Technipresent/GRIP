"""Meaning check: two non-generative checkers judge each claim-evidence pair in parallel. Both must agree."""
import asyncio
import sys
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


async def _score_all(checker, claim: str, passages: list[str]) -> list[float]:
    if hasattr(checker, "score_many"):
        return list(await checker.score_many(claim, passages))
    return list(await asyncio.gather(*(checker.score(claim, p) for p in passages)))


def _verdict(values: list[float], thresholds: Thresholds) -> PairVerdict:
    if all(v >= thresholds.support for v in values):
        return PairVerdict.SUPPORTS
    if all(v <= thresholds.contradict for v in values):
        return PairVerdict.CONTRADICTS
    return PairVerdict.UNCERTAIN


async def check_pairs(claim: str, passages: list[str], checkers: list, thresholds: Thresholds) -> list[PairResult]:
    """One batched call per checker for all of a claim's passages; checkers run in parallel."""
    if len(checkers) < 2:
        raise ValueError("meaning check requires two independent checkers")
    if not passages:
        return []
    raw = await asyncio.gather(*(_score_all(c, claim, passages) for c in checkers), return_exceptions=True)
    errors = []
    for c, r in zip(checkers, raw):
        if isinstance(r, BaseException) or len(r) != len(passages):
            errors.append(c.name)
            print(f"GRIP checker {c.name} failed: {r!r}", file=sys.stderr, flush=True)
    results = []
    for i in range(len(passages)):
        scores = tuple(Score(c.name, None if c.name in errors else round(float(r[i]), 4))
                       for c, r in zip(checkers, raw))
        if errors:
            results.append(PairResult(PairVerdict.UNCERTAIN, scores, tuple(errors)))
        else:
            results.append(PairResult(_verdict([s.value for s in scores], thresholds), scores))
    return results
