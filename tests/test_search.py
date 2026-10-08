from grip.contracts import Claim
from grip.planner import plan
from grip.search import gather
from tests.fakes import FakeProvider, FakeReader

CLAIM = Claim(id="c", text="Aspirin reduces fever in adults", subject="Aspirin")
PAGE = "Unrelated intro. Aspirin reduces fever in adults when taken correctly. Other text."


async def test_merges_providers_and_dedupes_same_url():
    brave = FakeProvider("brave", {"aspirin": ["https://nih.gov/a"]})
    exa = FakeProvider("exa", {"aspirin": ["https://nih.gov/a"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": exa},
                       FakeReader({"https://nih.gov/a": PAGE}))
    assert len(out.evidence) == 1
    assert out.evidence[0].providers == ("brave", "exa")


async def test_quote_is_exact_sentence_from_page():
    brave = FakeProvider("brave", {"aspirin": ["https://nih.gov/a"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")},
                       FakeReader({"https://nih.gov/a": PAGE}))
    assert out.evidence[0].quote == "Aspirin reduces fever in adults when taken correctly."
    assert out.evidence[0].quote in PAGE


async def test_forums_excluded():
    brave = FakeProvider("brave", {"aspirin": ["https://www.reddit.com/r/x", "https://quora.com/q"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")},
                       FakeReader({"https://www.reddit.com/r/x": PAGE, "https://quora.com/q": PAGE}))
    assert out.evidence == ()
    assert out.total_hits == 2


async def test_wrong_subject_page_rejected():
    brave = FakeProvider("brave", {"aspirin": ["https://a.org/x"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")},
                       FakeReader({"https://a.org/x": "Ibuprofen reduces fever in adults."}))
    assert out.evidence == ()


async def test_one_source_one_vote_per_domain():
    brave = FakeProvider("brave", {"aspirin": ["https://nih.gov/a", "https://nih.gov/b"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")},
                       FakeReader({"https://nih.gov/a": PAGE, "https://nih.gov/b": PAGE}))
    assert len(out.evidence) == 1


async def test_provider_failure_recorded_not_raised():
    brave = FakeProvider("brave", {"aspirin": ["https://nih.gov/a"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa", fail=True)},
                       FakeReader({"https://nih.gov/a": PAGE}))
    assert out.failed_providers == ("exa",)
    assert len(out.evidence) == 1


async def test_unreadable_page_skipped():
    brave = FakeProvider("brave", {"aspirin": ["https://nih.gov/a"]})
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")}, FakeReader({}))
    assert out.evidence == ()


async def test_evidence_order_is_deterministic():
    brave = FakeProvider("brave", {"aspirin": ["https://z.org/a", "https://b.org/a"]})
    pages = {"https://z.org/a": PAGE, "https://b.org/a": PAGE}
    out = await gather(CLAIM, plan(CLAIM), {"brave": brave, "exa": FakeProvider("exa")}, FakeReader(pages))
    assert [e.url for e in out.evidence] == ["https://b.org/a", "https://z.org/a"]
