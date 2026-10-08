import pytest

from grip.meaning import PairVerdict, Thresholds, check_pair
from tests.fakes import FakeChecker

T = Thresholds(support=0.8, contradict=0.2)


async def test_both_high_supports():
    r = await check_pair("c", "p", [FakeChecker("hhem", {}, 0.9), FakeChecker("minicheck", {}, 0.95)], T)
    assert r.verdict is PairVerdict.SUPPORTS
    assert [s.checker for s in r.scores] == ["hhem", "minicheck"]


async def test_both_low_contradicts():
    r = await check_pair("c", "p", [FakeChecker("hhem", {}, 0.05), FakeChecker("minicheck", {}, 0.1)], T)
    assert r.verdict is PairVerdict.CONTRADICTS


async def test_disagreement_is_uncertain():
    r = await check_pair("c", "p", [FakeChecker("hhem", {}, 0.9), FakeChecker("minicheck", {}, 0.1)], T)
    assert r.verdict is PairVerdict.UNCERTAIN


async def test_middle_scores_uncertain():
    r = await check_pair("c", "p", [FakeChecker("hhem", {}, 0.6), FakeChecker("minicheck", {}, 0.7)], T)
    assert r.verdict is PairVerdict.UNCERTAIN


async def test_checker_outage_is_uncertain():
    r = await check_pair("c", "p", [FakeChecker("hhem", {}, 0.9), FakeChecker("minicheck", {}, fail=True)], T)
    assert r.verdict is PairVerdict.UNCERTAIN
    assert r.errors == ("minicheck",)


async def test_needs_two_checkers():
    with pytest.raises(ValueError):
        await check_pair("c", "p", [FakeChecker("hhem", {}, 0.9)], T)
