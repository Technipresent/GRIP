"""Search and read: parallel search across providers, merged evidence with exact quotes."""
import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from grip.contracts import Claim
from grip.planner import PlannedQuery
from grip.reader import split_sentences

EXCLUDED_DOMAINS = ("reddit.com", "quora.com", "facebook.com", "x.com", "twitter.com", "tiktok.com",
                    "pinterest.com", "instagram.com", "stackexchange.com", "answers.yahoo.com")
STOPWORDS = {"the", "and", "for", "are", "was", "were", "with", "that", "this", "from", "has", "have",
             "had", "its", "into", "than", "then", "when", "who", "what", "which", "will", "can", "not",
             "but", "all", "any", "been", "being", "their", "there", "they", "them", "his", "her", "our"}
_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Evidence:
    url: str
    domain: str
    providers: tuple[str, ...]
    quote: str
    passage: str


@dataclass(frozen=True)
class SearchOutcome:
    evidence: tuple[Evidence, ...]
    total_hits: int
    failed_providers: tuple[str, ...]
    providers_tried: int


def domain_of(url: str) -> str:
    d = urlparse(url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def _excluded(domain: str) -> bool:
    return any(domain == x or domain.endswith("." + x) for x in EXCLUDED_DOMAINS)


def tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) >= 3 and w not in STOPWORDS}


def best_quote(claim: Claim, page: str) -> tuple[str, str] | None:
    subject = tokens(claim.subject)
    page_tokens = tokens(page)
    if not subject or not subject <= page_tokens:
        return None
    wanted = tokens(claim.text)
    sentences = split_sentences(page)
    best, best_score = None, 1
    for i, s in enumerate(sentences):
        st = tokens(s)
        if not st & subject:
            continue
        score = len(st & wanted)
        if score > best_score:
            best, best_score = i, score
    if best is None:
        return None
    passage = " ".join(sentences[max(0, best - 1): best + 2])
    return sentences[best], passage


async def gather(claim: Claim, planned: list[PlannedQuery], providers: dict, reader) -> SearchOutcome:
    jobs = [(name, q.text) for q in planned for name in q.providers if name in providers]
    results = await asyncio.gather(*(providers[n].search(t) for n, t in jobs), return_exceptions=True)

    failed, url_providers, total = set(), {}, 0
    for (name, _), res in zip(jobs, results):
        if isinstance(res, BaseException):
            failed.add(name)
            continue
        for hit in res:
            total += 1
            url_providers.setdefault(hit.url, set()).add(hit.provider)

    urls = sorted(u for u in url_providers if not _excluded(domain_of(u)))
    pages = await asyncio.gather(*(reader.read(u) for u in urls), return_exceptions=True)

    by_domain: dict[str, Evidence] = {}
    for url, page in zip(urls, pages):
        if isinstance(page, BaseException):
            continue
        found = best_quote(claim, page)
        dom = domain_of(url)
        if found and dom not in by_domain:
            by_domain[dom] = Evidence(url=url, domain=dom, providers=tuple(sorted(url_providers[url])),
                                      quote=found[0], passage=found[1])

    evidence = tuple(sorted(by_domain.values(), key=lambda e: e.url))
    tried = len({n for n, _ in jobs})
    return SearchOutcome(evidence=evidence, total_hits=total, failed_providers=tuple(sorted(failed)),
                         providers_tried=tried)
