"""Release gate: the same claims, five runs against a live GRIP, must give identical verdicts.
Usage: python proof/five_identical_runs.py https://grip.example.app claims.json"""
import json
import sys

import httpx


def main(base_url: str, claims_path: str) -> int:
    with open(claims_path, encoding="utf-8") as f:
        body = json.load(f)
    runs = []
    for _ in range(5):
        r = httpx.post(f"{base_url.rstrip('/')}/v1/ground", json=body, timeout=300)
        r.raise_for_status()
        runs.append([(x["id"], x["verdict"], x["deciding_rule"]) for x in r.json()["results"]])
    same = all(run == runs[0] for run in runs)
    print("PASS — five identical runs" if same else "FAIL — verdicts differ across runs")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
