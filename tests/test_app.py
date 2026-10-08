from fastapi.testclient import TestClient

from grip.app import create_app
from tests.test_engine import make_engine


def test_health():
    assert TestClient(create_app(make_engine())).get("/health").json() == {"status": "ok", "contract_version": "2.0"}


def test_ground_endpoint():
    body = {"claims": [{"id": "c1", "text": "Aspirin reduces fever in adults", "subject": "Aspirin"}]}
    r = TestClient(create_app(make_engine())).post("/v1/ground", json=body)
    assert r.status_code == 200
    assert r.json()["results"][0]["verdict"] == "Supported"


def test_bad_request_rejected():
    r = TestClient(create_app(make_engine())).post("/v1/ground", json={"claims": []})
    assert r.status_code == 422
