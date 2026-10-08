"""Locked decision 1: no generative model decides any verdict. Enforced by scanning the verdict path."""
import pathlib
import re

FORBIDDEN = [r"\bimport openai\b", r"\bfrom openai\b", r"\bimport anthropic\b", r"\bfrom anthropic\b",
             r"api\.openai\.com", r"api\.anthropic\.com", r"/v1/messages", r"chat/completions",
             r"\.generate\(", r"generativelanguage\.googleapis", r"AutoModelForCausalLM"]


def test_verdict_path_has_no_generative_model_calls():
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for folder in ("grip", "checker_service"):
        for f in (root / folder).rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            offenders += [f"{f.name}: {p}" for p in FORBIDDEN if re.search(p, text)]
    assert offenders == []
