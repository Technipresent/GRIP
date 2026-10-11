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
MAGNITUDE_WINDOW = 0.10
_QTY = re.compile(r"(?<![\d.,:])(\d[\d,]*(?:\.\d+)?)(?![\d:])\s*([a-zA-Z%]+)?")
_UNITS = {"m": "m", "metre": "m", "metres": "m", "meter": "m", "meters": "m",
          "km": "km", "kilometre": "km", "kilometres": "km", "kilometer": "km", "kilometers": "km",
          "ft": "ft", "feet": "ft", "foot": "ft", "mi": "mi", "mile": "mi", "miles": "mi",
          "kg": "kg", "kilograms": "kg", "lb": "lb", "lbs": "lb", "pounds": "lb",
          "years": "years", "year": "years", "people": "people", "%": "percent", "percent": "percent"}


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


@dataclass(frozen=True)
class Quantity:
    kind: str
    value: float
    unit: str | None
    step: float


def extract_quantities(text: str) -> list[Quantity]:
    out = []
    for raw, word in _QTY.findall(text):
        digits = raw.replace(",", "")
        decimals = len(digits.split(".")[1]) if "." in digits else 0
        value, step = float(digits), 10 ** -decimals
        word = (word or "").lower()
        if word in _MULT:
            value, step, word = value * _MULT[word], step * _MULT[word], ""
        unit = _UNITS.get(word)
        if unit == "percent":
            out.append(Quantity("percent", value, None, step))
        elif not unit and "," not in raw and "." not in raw and len(raw) == 4 and 1000 <= value <= 2099:
            out.append(Quantity("year", value, None, step))
        else:
            out.append(Quantity("number", value, unit, step))
    return out


def _comparable(c: Quantity, q: Quantity) -> bool:
    if c.kind != q.kind:
        return False
    if c.unit and q.unit != c.unit:
        return False
    if c.kind == "year":
        return True
    return abs(q.value - c.value) <= MAGNITUDE_WINDOW * max(abs(c.value), 1e-9)


def _same(c: Quantity, q: Quantity) -> bool:
    return abs(q.value - c.value) <= 0.5 * max(c.step, q.step) + 1e-9


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


# --- Session-288 hardening: zero false "true" calls (Founder bar) -------------------------------------------
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")
_STOP = {"the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "by", "with", "from", "as", "is",
         "was", "were", "are", "be", "been", "it", "its", "this", "that", "these", "those", "which", "who", "has",
         "have", "had", "his", "her", "their", "than", "then", "also", "about", "into", "over", "after", "before"}
_SECOND_LEVEL = {"co", "com", "gov", "ac", "org", "net", "edu"}


def _name_phrases(text: str) -> list[tuple[str, ...]]:
    """Runs of capitalised content words — 'Mount Everest', 'London' — skipping a common sentence opener."""
    words = _WORD.findall(text)
    phrases, run = [], []
    for i, w in enumerate(words):
        is_name = w[0].isupper() and len(w) > 1 and w.lower() not in _STOP
        if is_name:
            run.append(w.lower())
        elif run:
            phrases.append(tuple(run))
            run = []
    if run:
        phrases.append(tuple(run))
    return phrases


def anchored(claim: Claim, quote: str) -> bool:
    """The quote is about the claim's subject: every name phrase in the claim is present in the quote (its head
    word, the last word, is enough — 'Everest' satisfies 'Mount Everest'); with no names, at least half the
    subject's content words appear."""
    low = quote.lower()
    phrases = _name_phrases(claim.text)
    if phrases:
        return all(p[-1] in low for p in phrases)
    words = {w.lower() for w in _WORD.findall(claim.subject or claim.text) if w.lower() not in _STOP and len(w) > 2}
    return bool(words) and sum(1 for w in words if w in low) * 2 >= len(words)


def base_domain(domain: str) -> str:
    labels = domain.lower().strip(".").split(".")
    if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def corroborated(support) -> bool:
    """Independent-owner corroboration: two different owners agree, or one top-tier authority."""
    owners = {base_domain(e.domain) for e in support}
    return len(owners) >= 2 or any(authority_weight(e.domain) >= 3 for e in support)


# --- Session-288 round 2: failure classes found in the known-answer run -----------------------------------
_DEBUNK = re.compile(r"\b(myths?|misconceptions?|debunk\w*|hoax(es)?|not true|untrue|false(ly)?|disproven)\b", re.I)
_ATTRIBUTION = re.compile(
    r"\b(the (idea|notion|belief|claim) that|notion|legends?|rumou?rs?|supposedly|allegedly|fiction(al)?|"
    r"claim(s|ed|ing)? that|believe[sd]? that|argue[sd]? that|argued|theor(y|ies) that|says|said)\b", re.I)
_QUESTIONISH = re.compile(r"_{3,}|\?\s*$|^\s*(is|are|was|were|does|do|did|can|could|should|why|what|how)\b", re.I)
_OPINION = re.compile(
    r"\b(elegant|sophisticated|masterpiece|overpriced|overrated|underrated|belongs?|beautiful|delicious|"
    r"amazing|terrible|awful|stunning|boring|excellent|wonderful|disappointing|tasty|ugly|should|ought)\b", re.I)
_DEMONSTRATIVE = re.compile(r"^\s*(this|that|these|those)\b", re.I)
_COPULA = re.compile(r"^\s*(?:the\s+)?(.+?)\s+(is|are|was|were)\s+(?:a|an|the)?\s*(.+?)[.\s]*$", re.I)


def not_checkable(claim: Claim) -> str | None:
    """Opinions and unresolved references can never be Supported by search."""
    if _DEMONSTRATIVE.search(claim.text) and not _name_phrases(claim.text):
        return "unresolved-reference"
    if _OPINION.search(claim.text) and not extract_quantities(claim.text):
        return "opinion-not-checkable"
    return None


def framed_as_report(quote: str) -> bool:
    """The quote reports or questions the claim rather than asserting it."""
    return bool(_ATTRIBUTION.search(quote) or _DEBUNK.search(quote) or _QUESTIONISH.search(quote.strip()))


def copular_match(claim: Claim, quote: str) -> bool:
    """For 'X is a Y' claims the quote must assert it in that order: X, then is/are/was/were, then Y nearby."""
    m = _COPULA.match(claim.text)
    if not m:
        return True
    subj = [w.lower() for w in _WORD.findall(m.group(1)) if w.lower() not in _STOP]
    pred = [w.lower() for w in _WORD.findall(m.group(3)) if w.lower() not in _STOP]
    if not subj or not pred:
        return True
    if extract_quantities(m.group(3)):              # numeric predicate: exact-fact rules check the value
        return re.search(rf"\b{re.escape(subj[-1])}\b(?:\W+\w+){{0,3}}?\W+(is|are|was|were)\b", quote, re.I) is not None
    pat = (rf"\b{re.escape(subj[-1])}\b(?:\W+\w+){{0,3}}?\W+(is|are|was|were)\b(?:\W+\w+){{0,6}}?\W+"
           rf"{re.escape(pred[0])}\b")
    return re.search(pat, quote, re.I) is not None


def support_allowed(claim: Claim, quote: str) -> bool:
    return anchored(claim, quote) and not framed_as_report(quote) and copular_match(claim, quote)


def debunks(claim: Claim, quote: str) -> bool:
    return anchored(claim, quote) and bool(_DEBUNK.search(quote))


def _exact_votes(claim, claim_quantities, judged):
    votes = []
    for ev, res in judged:
        if debunks(claim, ev.quote):
            votes.append((ev, PairVerdict.CONTRADICTS))
            continue
        if not anchored(claim, ev.quote):
            continue                                    # a number about something else proves nothing
        quote_q = extract_quantities(ev.quote)
        found = [(c, q) for c in claim_quantities for q in quote_q if _comparable(c, q)]
        if not found:
            continue
        mismatch = any(not any(_same(c, q) for cc, q in found if cc is c) for c in {c for c, _ in found})
        if mismatch:
            votes.append((ev, PairVerdict.CONTRADICTS))
            continue
        every_fact = all(any(_same(c, q) for q in quote_q) for c in claim_quantities)
        if every_fact and res.verdict is not PairVerdict.CONTRADICTS and support_allowed(claim, ev.quote):
            votes.append((ev, PairVerdict.SUPPORTS))
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
    unchecked = not_checkable(claim)
    if unchecked:
        return Decision(Verdict.DISPUTED, unchecked, (), 0.0)

    claim_quantities = extract_quantities(claim.text)
    if claim_quantities:
        votes = _exact_votes(claim, claim_quantities, judged)
        if not votes:
            return Decision(Verdict.DISPUTED, "exact-facts-unconfirmed", (), 0.0)
        names = ("exact-facts-match", "exact-facts-mismatch")
    else:
        votes = []
        for ev, r in judged:
            if debunks(claim, ev.quote):
                votes.append((ev, PairVerdict.CONTRADICTS))
            elif r.verdict is PairVerdict.CONTRADICTS:
                votes.append((ev, r.verdict))
            elif r.verdict is PairVerdict.SUPPORTS and support_allowed(claim, ev.quote):
                votes.append((ev, r.verdict))
        if not votes:
            if any(r.errors for _, r in judged):
                rule = "checker-outage"
            elif any(r.verdict is PairVerdict.SUPPORTS for _, r in judged):
                rule = "support-not-about-subject"
            else:
                rule = "checkers-uncertain"
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
        if not corroborated(support):
            return Decision(Verdict.DISPUTED, "single-owner-support", tuple(support), 0.0)
        scope = _scope_words(claim.text)
        if scope and not any(scope & _scope_words(e.quote) for e in support):
            return Decision(Verdict.DISPUTED, "scope-not-confirmed", tuple(support), 0.0)
        if claim.stakes == "high" and s < 2:
            return Decision(Verdict.DISPUTED, "high-stakes-insufficient-support", tuple(support), 0.0)

    winning = s if verdict is Verdict.SUPPORTED else c
    return Decision(verdict, rule, tuple(sorted(quotes, key=lambda e: e.url)), round(winning / total, 3))
