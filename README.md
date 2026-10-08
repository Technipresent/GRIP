# GRIP — Grounding Engine (v2.0)

Decides, for each claim, whether public evidence supports it, contradicts it, or does not settle it, and proves the answer with exact quotes and links. GRIP grounds only; it never writes text. No generative model decides any verdict.

Specification: `docs/GRIP-ENGINE-SPEC-v2.0.md` (locked, Session-287).

## Flow
Request intake (plans searches) → Search and read (Brave and Exa in parallel, merged, exact quotes) → Meaning check (HHEM-2.1-Open and MiniCheck-FlanT5 in parallel; both must agree) → Rules engine (exact facts by rule; authority weighing; uncertain is Disputed) → Result.

## Services
- `grip` — the engine. `Dockerfile` at the root. Endpoints: `GET /health`, `POST /v1/ground`.
- `checker_service` — one deployment per checker (`CHECKER=hhem` or `CHECKER=minicheck`). `checker_service/Dockerfile`. Refuses to start if its self-test fails.

Environment: see `.env.example`.

## Tests
`pip install -r requirements-test.txt && python -m pytest -q`

## Release gates
1. All tests green (run in continuous integration on every push).
2. Known-answer bank passes against a live deployment.
3. `proof/five_identical_runs.py` passes against a live deployment.
4. Public benchmarks run and reported.
