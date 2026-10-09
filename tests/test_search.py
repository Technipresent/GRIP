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


async def test_sentence_sharing_only_subject_words_is_not_evidence():
    claim = Claim(id="c", text="Mount Everest is 8,849 metres tall", subject="Mount Everest")
    page = "Mount Everest is the ultimate dream for many climbers. Nothing else here."
    brave = FakeProvider("brave", {"everest": ["https://a.org/x"]})
    out = await gather(claim, plan(claim), {"brave": brave, "exa": FakeProvider("exa")},
                       FakeReader({"https://a.org/x": page}))
    assert out.evidence == ()


async def test_evidence_capped_to_most_relevant():
    from grip.search import MAX_EVIDENCE
    urls = [f"https://site{i:02d}.org/a" for i in range(MAX_EVIDENCE + 2)]
    pages = {u: PAGE for u in urls}
    strong = "Aspirin reduces fever in adults; in adults aspirin reliably reduces fever."
    pages[urls[-1]] = strong
    out = await gather(CLAIM, plan(CLAIM), {"brave": FakeProvider("brave", {"aspirin": urls}),
                                            "exa": FakeProvider("exa")}, FakeReader(pages))
    assert len(out.evidence) == MAX_EVIDENCE
    assert [e.url for e in out.evidence] == sorted(e.url for e in out.evidence)
