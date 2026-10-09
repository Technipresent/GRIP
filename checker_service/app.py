"""Self-hosted checker service. One deployment per checker: CHECKER=hhem or CHECKER=minicheck.
Non-generative use only: each model returns a support probability for (evidence, claim).
Run: uvicorn checker_service.app:build_app --factory --host 0.0.0.0 --port $PORT"""
import os
import threading
from typing import Callable

from fastapi import FastAPI
from pydantic import BaseModel, Field

ALLOWED = {"hhem": "vectara/hallucination_evaluation_model",
           "minicheck": "lytang/MiniCheck-Flan-T5-Large"}

Scorer = Callable[[list[tuple[str, str]]], list[float]]
INFER_CHUNK = int(os.environ.get("CHECKER_INFER_CHUNK") or 8)


class Pair(BaseModel):
    claim: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class ScoreRequest(BaseModel):
    pairs: list[Pair] = Field(min_length=1, max_length=64)


def load_hhem() -> Scorer:
    from transformers import AutoModelForSequenceClassification
    model = AutoModelForSequenceClassification.from_pretrained(ALLOWED["hhem"], trust_remote_code=True)
    model.eval()

    def score(pairs):
        return [float(x) for x in model.predict([(ev, cl) for cl, ev in pairs])]
    return score


def load_minicheck() -> Scorer:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(ALLOWED["minicheck"])
    model = AutoModelForSeq2SeqLM.from_pretrained(ALLOWED["minicheck"])
    model.eval()
    label_ids = [tok("0").input_ids[0], tok("1").input_ids[0]]

    def score(pairs):
        texts = [f"premise: {ev} hypothesis: {cl}" for cl, ev in pairs]
        enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
        start = torch.full((len(texts), 1), model.config.decoder_start_token_id)
        with torch.no_grad():
            logits = model(**enc, decoder_input_ids=start).logits[:, 0, label_ids]
        return torch.softmax(logits, dim=-1)[:, 1].tolist()
    return score


SELF_TEST = [("Paris is the capital of France.", "Paris is the capital and largest city of France.", True),
             ("Paris is the capital of Germany.", "Berlin is the capital of Germany.", False)]


def self_test(scorer: Scorer) -> bool:
    scores = scorer([(c, e) for c, e, _ in SELF_TEST])
    print(f"self-test scores (expect high, low): {[round(float(s), 4) for s in scores]}", flush=True)
    return all((s > 0.5) == expected for s, (_, _, expected) in zip(scores, SELF_TEST))


def create_checker_app(name: str, scorer: Scorer | None = None) -> FastAPI:
    if name not in ALLOWED:
        raise ValueError(f"unknown checker {name}; allowed: {sorted(ALLOWED)}")
    if scorer is None:
        scorer = load_hhem() if name == "hhem" else load_minicheck()
        if not self_test(scorer):
            raise RuntimeError(f"{name} failed its start-up self-test; refusing to serve")
    app = FastAPI(title=f"GRIP checker — {name}")
    # Session-288 (outage fix): inference is CPU-bound and blocking. It runs off the event loop (sync route,
    # FastAPI thread pool) one request at a time, in small chunks, so /health stays responsive and memory
    # stays bounded instead of the whole service stalling past the engine's timeout.
    lock = threading.Lock()

    @app.get("/health")
    async def health():
        return {"status": "ok", "checker": name}

    @app.post("/score")
    def score(req: ScoreRequest):
        pairs = [(p.claim, p.evidence) for p in req.pairs]
        values: list[float] = []
        with lock:
            for i in range(0, len(pairs), INFER_CHUNK):
                values.extend(scorer(pairs[i:i + INFER_CHUNK]))
        return {"scores": [round(min(1.0, max(0.0, float(v))), 6) for v in values]}

    return app


def build_app() -> FastAPI:
    return create_checker_app(os.environ["CHECKER"])
