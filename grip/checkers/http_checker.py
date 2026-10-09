"""Checker connector: calls a self-hosted checker service (HHEM or MiniCheck-FlanT5) over HTTP.

Session-288 (checker outage fix): small batches, a per-checker cap on requests in flight so a batch of
claims never floods a single-CPU checker past the timeout, and one retry on a timeout or server error.
"""
import asyncio

import httpx

BATCH = 16
MAX_IN_FLIGHT = 2
TIMEOUT_S = 300.0
RETRIES = 1


class HttpChecker:
    def __init__(self, name: str, base_url: str, client: httpx.AsyncClient, timeout: float = TIMEOUT_S,
                 max_in_flight: int = MAX_IN_FLIGHT, retries: int = RETRIES):
        self.name, self.base_url, self.client, self.timeout = name, base_url.rstrip("/"), client, timeout
        self.retries = max(0, int(retries))
        self._gate = asyncio.Semaphore(max(1, int(max_in_flight)))

    async def _post(self, chunk: list[str], claim: str) -> list[float]:
        last = None
        for _attempt in range(self.retries + 1):
            try:
                async with self._gate:
                    r = await self.client.post(f"{self.base_url}/score", timeout=self.timeout,
                                               json={"pairs": [{"claim": claim, "evidence": p} for p in chunk]})
                if r.status_code >= 500:
                    last = httpx.HTTPStatusError(f"server error {r.status_code}", request=r.request, response=r)
                    continue
                r.raise_for_status()
                return [float(v) for v in r.json()["scores"]]
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc
                continue
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
                raise RuntimeError(f"{self.name}: {exc!r}") from exc
        raise RuntimeError(f"{self.name}: {last!r}")

    async def score_many(self, claim: str, passages: list[str]) -> list[float]:
        values: list[float] = []
        for start in range(0, len(passages), BATCH):
            chunk = passages[start:start + BATCH]
            got = await self._post(chunk, claim)
            if len(got) != len(chunk) or not all(0.0 <= v <= 1.0 for v in got):
                raise RuntimeError(f"{self.name}: bad scores {got}")
            values.extend(got)
        return values

    async def score(self, claim: str, passage: str) -> float:
        return (await self.score_many(claim, [passage]))[0]
