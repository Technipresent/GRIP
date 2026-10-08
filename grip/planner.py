"""Request intake: plans the searches for one claim and routes each to providers."""
import re
from dataclasses import dataclass

from grip.contracts import Claim

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class PlannedQuery:
    text: str
    providers: tuple[str, ...]
    purpose: str


def plan(claim: Claim) -> list[PlannedQuery]:
    queries = [
        PlannedQuery(claim.text, ("brave", "exa"), "claim"),
        PlannedQuery(f"{claim.subject} earlier case before", ("exa",), "earlier"),
        PlannedQuery(f"alternatives to {claim.subject}", ("exa",), "alternatives"),
    ]
    numbers = [n.replace(",", "") for n in _NUMBER.findall(claim.text)]
    if numbers:
        quoted = " ".join(f'"{n}"' for n in numbers)
        queries.append(PlannedQuery(f"{claim.subject} {quoted}", ("brave",), "exact"))
    return queries
