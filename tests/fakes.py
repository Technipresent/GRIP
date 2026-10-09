"""Test doubles shared across the GRIP test suite."""
from grip.providers.base import ProviderError, SearchHit


class FakeProvider:
    def __init__(self, name, results=None, fail=False):
        self.name = name
        self.results = results or {}
        self.fail = fail
        self.calls = []

    async def search(self, query, limit=10):
        self.calls.append(query)
        if self.fail:
            raise ProviderError(f"{self.name} unavailable")
        hits = []
        for key, urls in self.results.items():
            if key.lower() in query.lower():
                hits.extend(SearchHit(url=u, title=u, snippet="", provider=self.name) for u in urls)
        return hits[:limit]


class FakeReader:
    def __init__(self, pages):
        self.pages = pages

    async def read(self, url):
        if url not in self.pages:
            raise RuntimeError("unreadable")
        return self.pages[url]


class FakeChecker:
    """Scores by keyword: passage containing a listed phrase gets that score."""

    def __init__(self, name, table, default=0.5, fail=False):
        self.name = name
        self.table = table
        self.default = default
        self.fail = fail

    async def score(self, claim, passage):
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        for phrase, value in self.table.items():
            if phrase.lower() in passage.lower():
                return value
        return self.default


class BatchChecker(FakeChecker):
    """Counts batched calls; scores each passage like FakeChecker."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_calls = 0

    async def score_many(self, claim, passages):
        self.batch_calls += 1
        return [await self.score(claim, p) for p in passages]
