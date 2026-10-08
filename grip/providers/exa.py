"""Exa search adapter (meaning index)."""
import httpx

from grip.providers.base import ProviderError, SearchHit

URL = "https://api.exa.ai/search"


class ExaProvider:
    name = "exa"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self.api_key = api_key
        self.client = client

    async def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        if not self.api_key:
            raise ProviderError("exa: no key configured")
        try:
            r = await self.client.post(URL, json={"query": query, "numResults": limit},
                                       headers={"x-api-key": self.api_key}, timeout=15)
            r.raise_for_status()
            results = r.json().get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"exa: {exc}") from exc
        return [SearchHit(url=x["url"], title=x.get("title") or "", snippet=x.get("text") or "",
                          provider=self.name) for x in results[:limit] if x.get("url")]
