from grip.contracts import Claim, Verdict
from grip.meaning import PairResult, PairVerdict
from grip.rules import authority_weight, decide, extract_numbers
from grip.search import Evidence, SearchOutcome

S, C, U = PairVerdict.SUPPORTS, PairVerdict.CONTRADICTS, PairVerdict.UNCERTAIN


def ev(url, quote="Aspirin reduces fever."):
    return Evidence(url=url, domain=url.split("/")[2], providers=("brave",), quote=quote, passage=quote)


def pr(v, errors=()):
    return PairResult(verdict=v, scores=(), errors=errors)


def outcome(evidence=(), hits=5, failed=(), providers=2):
    return SearchOutcome(evidence=tuple(evidence), total_hits=hits, failed_providers=tuple(failed),
                         providers_tried=providers)


CL = Claim(id="c", text="Aspirin reduces fever", subject="Aspirin")


def test_all_providers_down_is_disputed():
    d = decide(CL, outcome(hits=0, failed=("brave", "exa")), [])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "provider-outage")


def test_zero_results_anywhere_is_no_evidence():
    d = decide(CL, outcome(hits=0), [])
    assert (d.verdict, d.rule) == (Verdict.NO_EVIDENCE, "zero-results-anywhere")


def test_zero_results_with_one_provider_down_is_disputed_not_no_evidence():
    d = decide(CL, outcome(hits=0, failed=("exa",)), [])
    assert d.verdict is Verdict.DISPUTED


def test_hits_but_no_usable_evidence_is_disputed():
    d = decide(CL, outcome(), [])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "no-usable-evidence")


def test_agreeing_support():
    a, b = ev("https://a.org/x"), ev("https://b.org/x")
    d = decide(CL, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.SUPPORTED, "sources-agree-support")
    assert d.quotes == (a, b)


def test_agreeing_contradiction():
    e = ev("https://a.org/x")
    d = decide(CL, outcome([e]), [(e, pr(C))])
    assert d.verdict is Verdict.CONTRADICTED


def test_too_close_is_disputed():
    a, b = ev("https://a.org/x"), ev("https://b.org/x")
    d = decide(CL, outcome([a, b]), [(a, pr(S)), (b, pr(C))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "too-close")


def test_authority_outweighs():
    gov, blog1 = ev("https://nih.gov/x"), ev("https://blog.com/x")
    d = decide(CL, outcome([gov, blog1]), [(gov, pr(S)), (blog1, pr(C))])
    assert (d.verdict, d.rule) == (Verdict.SUPPORTED, "weighed-majority")


def test_all_uncertain_is_disputed():
    e = ev("https://a.org/x")
    d = decide(CL, outcome([e]), [(e, pr(U))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "checkers-uncertain")


def test_checker_outage_is_disputed():
    e = ev("https://a.org/x")
    d = decide(CL, outcome([e]), [(e, pr(U, errors=("minicheck",)))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "checker-outage")


def test_high_stakes_single_ordinary_source_is_not_true():
    hs = Claim(id="c", text="Aspirin reduces fever", subject="Aspirin", stakes="high")
    e = ev("https://a.org/x")
    d = decide(hs, outcome([e]), [(e, pr(S))])
    assert d.verdict is Verdict.DISPUTED


def test_scope_word_must_appear_in_support():
    cl = Claim(id="c", text="Aspirin was the first painkiller", subject="Aspirin")
    a, b = ev("https://a.org/x", "Aspirin is a painkiller."), ev("https://b.org/x", "Aspirin is a painkiller.")
    d = decide(cl, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "scope-not-confirmed")


def test_scope_word_present_supports():
    cl = Claim(id="c", text="Aspirin was the first painkiller", subject="Aspirin")
    q = "Aspirin was the first synthetic painkiller."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(cl, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert d.verdict is Verdict.SUPPORTED


def test_exact_number_match_blocked_when_checker_contradicts():
    cl = Claim(id="c", text="Everest is 8,849 metres tall", subject="Everest")
    q = "Everest stands 8849 metres above sea level."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(cl, outcome([a, b]), [(a, pr(C)), (b, pr(C))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "exact-facts-unconfirmed")


def test_exact_number_mismatch_contradicts():
    cl = Claim(id="c", text="Everest is 9,100 metres tall", subject="Everest")
    e = ev("https://a.org/x", "Everest stands 8849 metres above sea level.")
    d = decide(cl, outcome([e]), [(e, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.CONTRADICTED, "exact-facts-mismatch")


def test_unit_equivalence():
    assert extract_numbers("2.5 million people") == extract_numbers("2,500,000 people")
    assert extract_numbers("about 40%") == {("percent", 40.0)}
    assert extract_numbers("in 1897") == {("year", 1897.0)}


def test_authority_tiers():
    assert authority_weight("nih.gov") == 3
    assert authority_weight("www.who.int") == 3
    assert authority_weight("en.wikipedia.org") == 2
    assert authority_weight("blog.com") == 1


EV = Claim(id="c", text="Mount Everest is 8,849 metres tall", subject="Mount Everest")


def _exact(quote):
    a, b = ev("https://a.org/x", quote), ev("https://b.org/x", quote)
    return decide(EV, outcome([a, b]), [(a, pr(U)), (b, pr(U))])


def test_more_precise_figure_that_rounds_to_claim_matches():
    assert _exact("Everest's official height is 8,848.86 metres.").verdict is Verdict.SUPPORTED


def test_unit_suffix_attached_matches():
    assert _exact("Everest, the tallest peak at 8,849m.").verdict is Verdict.SUPPORTED


def test_close_figure_in_same_unit_contradicts():
    assert _exact("Everest is 8,848 metres high.").verdict is Verdict.CONTRADICTED


def test_other_unit_and_unrelated_numbers_ignored():
    d = _exact("It is 29,032 feet; summit reached at 11:30 a.m.")
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "exact-facts-unconfirmed")


def test_far_off_magnitude_ignored():
    d = _exact("Base camp sits at 5,300 metres.")
    assert d.verdict is Verdict.DISPUTED


# --- Session-288 hardening: zero false "true" calls ------------------------------------------------------
from grip.rules import anchored, base_domain  # noqa: E402

TOWER = Claim(id="t", text="The Eiffel Tower in London was completed in 1889", subject="Eiffel Tower")


def test_number_about_another_subject_never_supports():
    q = "Construction finished in 1889 after two years of work."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(TOWER, outcome([a, b]), [(a, pr(U)), (b, pr(U))])
    assert d.verdict is not Verdict.SUPPORTED


def test_wrong_place_name_blocks_support_even_when_number_matches():
    q = "The Eiffel Tower in Paris was completed in 1889."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(TOWER, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert d.verdict is not Verdict.SUPPORTED


def test_every_number_in_claim_must_be_confirmed():
    cl = Claim(id="c", text="Everest is 8,849 metres tall and was first climbed in 1953", subject="Everest")
    q = "Everest is 8,849 metres tall."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(cl, outcome([a, b]), [(a, pr(U)), (b, pr(U))])
    assert d.verdict is not Verdict.SUPPORTED


def test_single_owner_support_is_disputed():
    e = ev("https://a.org/x")
    d = decide(CL, outcome([e]), [(e, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "single-owner-support")


def test_mirrors_of_one_owner_do_not_corroborate():
    a, b = ev("https://en.wikipedia.org/x"), ev("https://fr.wikipedia.org/x")
    d = decide(CL, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "single-owner-support")


def test_one_top_tier_authority_is_enough():
    e = ev("https://www.nih.gov/x")
    d = decide(CL, outcome([e]), [(e, pr(S))])
    assert d.verdict is Verdict.SUPPORTED


def test_checker_support_not_about_subject_is_disputed():
    q = "Ibuprofen reduces fever."
    a, b = ev("https://a.org/x", q), ev("https://b.org/x", q)
    d = decide(CL, outcome([a, b]), [(a, pr(S)), (b, pr(S))])
    assert (d.verdict, d.rule) == (Verdict.DISPUTED, "support-not-about-subject")


def test_anchoring_head_word_and_base_domain():
    assert anchored(EV, "Everest rises above the Khumbu.")
    assert not anchored(TOWER, "The Eiffel Tower in Paris.")
    assert base_domain("news.bbc.co.uk") == "bbc.co.uk"
    assert base_domain("en.wikipedia.org") == "wikipedia.org"
