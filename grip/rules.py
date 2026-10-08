"""Rules engine: deterministic verdicts. Exact facts decided by rule; meaning by agreed checkers; ties never guessed."""
import re
from dataclasses import dataclass

from grip.contracts import Claim, Verdict
from grip.meaning import PairResult, PairVerdict
from grip.search import Evidence, SearchOutcome

_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(%|percent\b|thousand\b|million\b|billion\b|trillion\b|k\b)?",
                  re.IGNORECASE)
_MULT = {"thousand": 1e3, "k": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
SCOPE_WORDS = ("first", "only", "largest", "smallest", "oldest", "newest", "biggest", "highest", "lowest",
               "best", "worst", "never", "always", "sole", "unique", "the standard")
AUTHORITY = {3: ("gov", "edu", "who.int", "europa.eu", "un.org", "nih.gov", "gc.ca", "gov.uk"),
             2: ("wikipedia.org", "britannica.com", "nature.com", "science.org", "reuters.com", "apnews.com")}
WEIGH_RATIO = 3.0


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    rule: str
    quotes: tuple[Evidence, ...]
    confidence: float


def extract_numbers(text: str) -> set[tuple[str, float]]:
    out = set()
    for raw, unit in _NUM.findall(text):
        value = float(raw.replace(",", ""))
        unit = (unit or "").lower()
        if unit in ("%", "percent"):
            out.add(("percent", value))
        elif unit in _MULT:
            out.add(("number", value * _MULT[unit]))
        elif "," not in raw and "." not in raw and len(raw) == 4 and 1000 <= value <= 2099:
            out.add(("year", value))
        else:
            out.add(("number", value))
    return out


def authority_weight(domain: str) -> int:
    domain = domain.lower()
    for weight, suffixes in AUTHORITY.items():
        for s in suffixes:
            if domain == s or domain.endswith("." + s):
                return weight
    return 1


def _scope_words(text: str) -> set[str]:
    low = f" {text.lower()} "
    return {w for w in SCOPE_WORDS if f" {w} " in low}


def _exact_votes(claim_numbers, judged):
    kinds = {k for k, _ in claim_numbers}
    votes = []
    for ev, _ in judged:
        q = extract_numbers(ev.quote)
        if q & claim_numbers:
            votes.append((ev, PairVerdict.SUPPORTS))
        elif {k for k, _ in q} & kinds:
            votes.append((ev, PairVerdict.CONTRADICTS))
    return votes


def decide(claim: Claim, outcome: SearchOutcome, judged: list[tuple[Evidence, PairResult]]) -> Decision:
    if outcome.providers_tried and len(outcome.failed_providers) >= outcome.providers_tried:
        return Decision(Verdict.DISPUTED, "provider-outage", (), 0.0)
    if outcome.total_hits == 0:
        if outcome.failed_providers:
            return Decision(Verdict.DISPUTED, "partial-outage-no-results", (), 0.0)
        return Decision(Verdict.NO_EVIDENCE, "zero-results-anywhere", (), 0.0)
    if not judged:
        return Decision(Verdict.DISPUTED, "no-usable-evidence", (), 0.0)

    claim_numbers = extract_numbers(claim.text)
    if claim_numbers:
        votes = _exact_votes(claim_numbers, judged)
        if not votes:
            return Decision(Verdict.DISPUTED, "exact-facts-unconfirmed", (), 0.0)
        names = ("exact-facts-match", "exact-facts-mismatch")
    else:
        votes = [(ev, r.verdict) for ev, r in judged if r.verdict is not PairVerdict.UNCERTAIN]
        if not votes:
            rule = "checker-outage" if any(r.errors for _, r in judged) else "checkers-uncertain"
            return Decision(Verdict.DISPUTED, rule, (), 0.0)
        names = ("sources-agree-support", "sources-agree-contradict")

    support = [ev for ev, v in votes if v is PairVerdict.SUPPORTS]
    against = [ev for ev, v in votes if v is PairVerdict.CONTRADICTS]
    s = sum(authority_weight(e.domain) for e in support)
    c = sum(authority_weight(e.domain) for e in against)
    total = s + c

    if s and not c:
        verdict, rule, quotes = Verdict.SUPPORTED, names[0], support
    elif c and not s:
        verdict, rule, quotes = Verdict.CONTRADICTED, names[1], against
    elif s >= WEIGH_RATIO * c:
        verdict, rule, quotes = Verdict.SUPPORTED, "weighed-majority", support
    elif c >= WEIGH_RATIO * s:
        verdict, rule, quotes = Verdict.CONTRADICTED, "weighed-majority", against
    else:
        return Decision(Verdict.DISPUTED, "too-close", tuple(support + against), 0.0)

    if verdict is Verdict.SUPPORTED:
        scope = _scope_words(claim.text)
        if scope and not any(scope & _scope_words(e.quote) for e in support):
            return Decision(Verdict.DISPUTED, "scope-not-confirmed", tuple(support), 0.0)
        if claim.stakes == "high" and s < 2:
            return Decision(Verdict.DISPUTED, "high-stakes-insufficient-support", tuple(support), 0.0)

    winning = s if verdict is Verdict.SUPPORTED else c
    return Decision(verdict, rule, tuple(sorted(quotes, key=lambda e: e.url)), round(winning / total, 3))
