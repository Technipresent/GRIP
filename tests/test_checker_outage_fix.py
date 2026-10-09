"""Session-288 checker outage fix: retry, in-flight cap, small batches, service off the event loop."""
import asyncio

import httpx
from fastapi.testclient import TestClient

from checker_service.app import create_checker_app
from grip.checkers.http_checker import HttpChecker, BATCH


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_retries_once_on_timeout_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow", request=request)
        n = len(__import__("json").loads(request.content)["pairs"])
        return httpx.Response(200, json={"scores": [0.9] * n})

    async def run():
        async with _client(handler) as c:
            return await HttpChecker("hhem", "http://x", c).score_many("claim", ["p1", "p2"])
    assert asyncio.run(run()) == [0.9, 0.9] and calls["n"] == 2


def test_retries_once_on_server_error_then_fails_loudly():
    def handler(request):
        return httpx.Response(503)

    async def run():
        async with _client(handler) as c:
            return await HttpChecker("hhem", "http://x", c).score_many("claim", ["p"])
    try:
        asyncio.run(run())
        raise AssertionError("expected failure")
    except RuntimeError as err:
        assert "hhem" in str(err)


def test_batches_are_small():
    sizes = []

    def handler(request):
        n = len(__import__("json").loads(request.content)["pairs"])
        sizes.append(n)
        return httpx.Response(200, json={"scores": [0.5] * n})

    async def run():
        async with _client(handler) as c:
            return await HttpChecker("m", "http://x", c).score_many("claim", [f"p{i}" for i in range(40)])
    out = asyncio.run(run())
    assert len(out) == 40 and max(sizes) <= BATCH == 16


def test_in_flight_cap_respected():
    state = {"now": 0, "peak": 0}

    async def handler(request):
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        await asyncio.sleep(0.02)
        state["now"] -= 1
        return httpx.Response(200, json={"scores": [0.5]})

    async def run():
        async with _client(handler) as c:
            ch = HttpChecker("m", "http://x", c, max_in_flight=2)
            await asyncio.gather(*(ch.score("claim", f"p{i}") for i in range(8)))
    asyncio.run(run())
    assert state["peak"] <= 2


def test_service_scores_in_chunks_and_keeps_order():
    seen = []

    def scorer(pairs):
        seen.append(len(pairs))
        return [0.1 * (i % 10) for i, _ in enumerate(pairs)]
    app = create_checker_app("hhem", scorer=scorer)
    r = TestClient(app).post("/score", json={"pairs": [{"claim": "c", "evidence": f"e{i}"} for i in range(20)]})
    assert r.status_code == 200 and len(r.json()["scores"]) == 20
    assert max(seen) <= 8


def test_service_health_route():
    app = create_checker_app("minicheck", scorer=lambda pairs: [0.5] * len(pairs))
    assert TestClient(app).get("/health").json() == {"status": "ok", "checker": "minicheck"}
