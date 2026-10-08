import json

import httpx
import pytest
from fastapi.testclient import TestClient

from checker_service.app import create_checker_app
from grip.checkers.http_checker import HttpChecker


async def test_http_checker_posts_pair_and_reads_score():
    def handler(request):
        body = json.loads(request.content)
        assert body == {"pairs": [{"claim": "c", "evidence": "p"}]}
        return httpx.Response(200, json={"scores": [0.87]})
    chk = HttpChecker("hhem", "http://chk", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await chk.score("c", "p") == 0.87


async def test_http_checker_rejects_out_of_range():
    chk = HttpChecker("hhem", "http://chk", httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"scores": [1.7]}))))
    with pytest.raises(RuntimeError):
        await chk.score("c", "p")


async def test_http_checker_raises_on_error_status():
    chk = HttpChecker("hhem", "http://chk", httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(503))))
    with pytest.raises(RuntimeError):
        await chk.score("c", "p")


def test_checker_service_scores_with_injected_scorer():
    app = create_checker_app("hhem", scorer=lambda pairs: [0.5 for _ in pairs])
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok", "checker": "hhem"}
    r = client.post("/score", json={"pairs": [{"claim": "a", "evidence": "b"}, {"claim": "c", "evidence": "d"}]})
    assert r.json() == {"scores": [0.5, 0.5]}


def test_checker_service_refuses_unknown_model():
    with pytest.raises(ValueError):
        create_checker_app("gpt", scorer=lambda p: [])
