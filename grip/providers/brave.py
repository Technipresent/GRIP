"""Brave search adapter (keyword index)."""
import httpx

from grip.providers.base import ProviderError, SearchHit

URL = "https://api.search.brave.com/res/v1/web/search"


class BraveProvider:
    name = "brave"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self.api_key = api_key
        self.client = client

    async def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        if not self.api_key:
            raise ProviderError("brave: no key configured")
        try:
            r = await self.client.get(URL, params={"q": query, "count": limit},
                                      headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                                      timeout=15)
            r.raise_for_status()
            results = r.json().get("web", {}).get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"brave: {exc}") from exc
        return [SearchHit(url=x["url"], title=x.get("title", ""), snippet=x.get("description", ""),
                          provider=self.name) for x in results[:limit] if x.get("url")]
