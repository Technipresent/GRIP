"""Checker connector: calls a self-hosted checker service (HHEM or MiniCheck-FlanT5) over HTTP."""
import httpx

BATCH = 64


class HttpChecker:
    def __init__(self, name: str, base_url: str, client: httpx.AsyncClient, timeout: float = 120):
        self.name, self.base_url, self.client, self.timeout = name, base_url.rstrip("/"), client, timeout

    async def score_many(self, claim: str, passages: list[str]) -> list[float]:
        values: list[float] = []
        for start in range(0, len(passages), BATCH):
            chunk = passages[start:start + BATCH]
            try:
                r = await self.client.post(f"{self.base_url}/score", timeout=self.timeout,
                                           json={"pairs": [{"claim": claim, "evidence": p} for p in chunk]})
                r.raise_for_status()
                got = [float(v) for v in r.json()["scores"]]
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
                raise RuntimeError(f"{self.name}: {exc!r}") from exc
            if len(got) != len(chunk) or not all(0.0 <= v <= 1.0 for v in got):
                raise RuntimeError(f"{self.name}: bad scores {got}")
            values.extend(got)
        return values

    async def score(self, claim: str, passage: str) -> float:
        return (await self.score_many(claim, [passage]))[0]
