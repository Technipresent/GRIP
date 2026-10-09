import pytest
from fastapi.testclient import TestClient

from grip.app import build_app, create_app
from tests.test_engine import make_engine

KEY = "k" * 40
BODY = {"claims": [{"id": "c1", "text": "Aspirin reduces fever in adults", "subject": "Aspirin"}]}


def test_health():
    assert TestClient(create_app(make_engine())).get("/health").json() == {"status": "ok", "contract_version": "2.0"}


def test_ground_endpoint():
    r = TestClient(create_app(make_engine())).post("/v1/ground", json=BODY)
    assert r.status_code == 200
    assert r.json()["results"][0]["verdict"] == "Supported"


def test_bad_request_rejected():
    r = TestClient(create_app(make_engine())).post("/v1/ground", json={"claims": []})
    assert r.status_code == 422


def test_ground_requires_key_when_configured():
    client = TestClient(create_app(make_engine(), api_key=KEY))
    assert client.post("/v1/ground", json=BODY).status_code == 401
    assert client.post("/v1/ground", json=BODY, headers={"X-GRIP-Key": "wrong"}).status_code == 401
    assert client.post("/v1/ground", json=BODY, headers={"X-GRIP-Key": KEY}).status_code == 200


def test_health_open_without_key():
    assert TestClient(create_app(make_engine(), api_key=KEY)).get("/health").status_code == 200


def test_build_app_refuses_without_strong_key(monkeypatch):
    monkeypatch.setenv("GRIP_API_KEY", "short")
    with pytest.raises(RuntimeError):
        build_app()
