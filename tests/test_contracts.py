import pytest
from pydantic import ValidationError

from grip.contracts import CONTRACT_VERSION, Claim, GroundRequest, Verdict


def test_contract_version_is_frozen():
    assert CONTRACT_VERSION == "2.0"


def test_verdict_values_are_the_four_allowed():
    assert {v.value for v in Verdict} == {
        "Supported", "Contradicted", "Disputed", "No evidence it exists"}


def test_claim_requires_text_and_subject():
    with pytest.raises(ValidationError):
        Claim(id="c1", text="", subject="x")
    with pytest.raises(ValidationError):
        Claim(id="c1", text="x", subject="")


def test_request_rejects_empty_batch():
    with pytest.raises(ValidationError):
        GroundRequest(claims=[])


def test_request_rejects_duplicate_ids():
    c = Claim(id="c1", text="t", subject="s")
    with pytest.raises(ValidationError):
        GroundRequest(claims=[c, c])


def test_stakes_default_normal():
    assert Claim(id="c1", text="t", subject="s").stakes == "normal"
