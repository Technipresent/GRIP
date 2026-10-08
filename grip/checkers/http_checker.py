"""Checker connector: calls a self-hosted checker service (HHEM or MiniCheck-FlanT5) over HTTP."""
import httpx


class HttpChecker:
    def __init__(self, name: str, base_url: str, client: httpx.AsyncClient):
        self.name, self.base_url, self.client = name, base_url.rstrip("/"), client

    async def score(self, claim: str, passage: str) -> float:
        try:
            r = await self.client.post(f"{self.base_url}/score", timeout=30,
                                       json={"pairs": [{"claim": claim, "evidence": passage}]})
            r.raise_for_status()
            value = float(r.json()["scores"][0])
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            raise RuntimeError(f"{self.name}: {exc}") from exc
        if not 0.0 <= value <= 1.0:
            raise RuntimeError(f"{self.name}: score out of range {value}")
        return value
