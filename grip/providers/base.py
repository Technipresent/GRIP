"""Fixed connector every hired search provider implements. Providers are replaceable."""
from dataclasses import dataclass
from typing import Protocol


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str
    snippet: str
    provider: str


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, limit: int = 10) -> list[SearchHit]: ...
