"""GRIP engine: request intake -> search and read -> meaning check -> rules engine -> result."""
import asyncio

from grip.contracts import CheckerScore, Claim, ClaimResult, GroundRequest, GroundResponse, Quote
from grip.meaning import Thresholds, check_pairs
from grip.planner import plan
from grip.rules import decide
from grip.search import gather


class Engine:
    def __init__(self, providers: dict, reader, checkers: list, thresholds: Thresholds):
        if len(checkers) < 2:
            raise ValueError("GRIP requires two independent checkers")
        self.providers, self.reader, self.checkers, self.thresholds = providers, reader, checkers, thresholds

    async def ground_claim(self, claim: Claim) -> ClaimResult:
        outcome = await gather(claim, plan(claim), self.providers, self.reader)
        pairs = await check_pairs(claim.text, [ev.passage for ev in outcome.evidence],
                                  self.checkers, self.thresholds)
        judged = list(zip(outcome.evidence, pairs))
        d = decide(claim, outcome, judged)
        return ClaimResult(
            id=claim.id, verdict=d.verdict, deciding_rule=d.rule, confidence=d.confidence,
            quotes=[Quote(text=e.quote, url=e.url, providers=list(e.providers)) for e in d.quotes],
            checker_scores=[CheckerScore(checker=s.checker, score=s.value, url=ev.url)
                            for ev, r in judged for s in r.scores],
        )

    async def ground(self, request: GroundRequest) -> GroundResponse:
        results = await asyncio.gather(*(self.ground_claim(c) for c in request.claims))
        return GroundResponse(results=list(results))
