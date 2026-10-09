"""GRIP HTTP service. Run: uvicorn grip.app:build_app --factory --host 0.0.0.0 --port $PORT"""
import hmac
import os

import httpx
from fastapi import FastAPI, Header, HTTPException

from grip.checkers.http_checker import HttpChecker
from grip.contracts import CONTRACT_VERSION, GroundRequest, GroundResponse
from grip.engine import Engine
from grip.meaning import Thresholds
from grip.providers.brave import BraveProvider
from grip.providers.exa import ExaProvider
from grip.reader import DirectReader


def create_app(engine: Engine, api_key: str | None = None) -> FastAPI:
    app = FastAPI(title="GRIP Grounding Engine", version="2.0.0")

    def authorise(supplied: str | None) -> None:
        if api_key and not (supplied and hmac.compare_digest(supplied, api_key)):
            raise HTTPException(status_code=401, detail="missing or wrong X-GRIP-Key")

    @app.get("/health")
    async def health():
        return {"status": "ok", "contract_version": CONTRACT_VERSION}

    @app.post("/v1/ground", response_model=GroundResponse)
    async def ground(request: GroundRequest, x_grip_key: str | None = Header(default=None)):
        authorise(x_grip_key)
        return await engine.ground(request)

    return app


def build_engine_from_env() -> Engine:
    client = httpx.AsyncClient()
    providers = {"brave": BraveProvider(os.environ.get("BRAVE_API_KEY", ""), client),
                 "exa": ExaProvider(os.environ.get("EXA_API_KEY", ""), client)}
    checkers = [HttpChecker("hhem", os.environ["HHEM_URL"], client),
                HttpChecker("minicheck", os.environ["MINICHECK_URL"], client)]
    thresholds = Thresholds(float(os.environ.get("SUPPORT_THRESHOLD", "0.8")),
                            float(os.environ.get("CONTRADICT_THRESHOLD", "0.2")))
    return Engine(providers, DirectReader(client), checkers, thresholds)


def build_app() -> FastAPI:
    api_key = os.environ.get("GRIP_API_KEY", "")
    if len(api_key) < 32:
        raise RuntimeError("GRIP_API_KEY missing or shorter than 32 characters; refusing to serve")
    return create_app(build_engine_from_env(), api_key=api_key)
