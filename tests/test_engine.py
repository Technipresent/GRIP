from grip.contracts import Claim, GroundRequest, Verdict
from grip.engine import Engine
from grip.meaning import Thresholds
from tests.fakes import FakeChecker, FakeProvider, FakeReader

PAGE = "Intro. Aspirin reduces fever in adults when taken correctly. End."


def make_engine(exa_fail=False, brave_fail=False, checker_fail=False):
    providers = {
        "brave": FakeProvider("brave", {"aspirin": ["https://nih.gov/a"]}, fail=brave_fail),
        "exa": FakeProvider("exa", {"aspirin": ["https://who.int/b"]}, fail=exa_fail),
    }
    reader = FakeReader({"https://nih.gov/a": PAGE, "https://who.int/b": PAGE})
    checkers = [FakeChecker("hhem", {"fever": 0.93}), FakeChecker("minicheck", {"fever": 0.9}, fail=checker_fail)]
    return Engine(providers, reader, checkers, Thresholds(0.8, 0.2))


REQ = GroundRequest(claims=[Claim(id="c1", text="Aspirin reduces fever in adults", subject="Aspirin")])


async def test_end_to_end_supported_with_quotes_and_rule():
    res = await make_engine().ground(REQ)
    r = res.results[0]
    assert r.verdict is Verdict.SUPPORTED
    assert r.deciding_rule == "sources-agree-support"
    assert {q.url for q in r.quotes} == {"https://nih.gov/a", "https://who.int/b"}
    assert {s.checker for s in r.checker_scores} == {"hhem", "minicheck"}
    assert res.contract_version == "2.0"


async def test_five_runs_identical():
    runs = [(await make_engine().ground(REQ)).model_dump_json() for _ in range(5)]
    assert len(set(runs)) == 1


async def test_one_provider_down_still_grounds():
    r = (await make_engine(exa_fail=True).ground(REQ)).results[0]
    assert r.verdict is Verdict.SUPPORTED


async def test_all_providers_down_disputed():
    r = (await make_engine(exa_fail=True, brave_fail=True).ground(REQ)).results[0]
    assert r.verdict is Verdict.DISPUTED


async def test_checker_down_disputed_never_wrong():
    r = (await make_engine(checker_fail=True).ground(REQ)).results[0]
    assert r.verdict is Verdict.DISPUTED


async def test_batch_preserves_order():
    req = GroundRequest(claims=[
        Claim(id="b", text="Aspirin reduces fever in adults", subject="Aspirin"),
        Claim(id="a", text="Zorblax cures sadness", subject="Zorblax")])
    res = await make_engine().ground(req)
    assert [r.id for r in res.results] == ["b", "a"]
    assert res.results[1].verdict is Verdict.NO_EVIDENCE
