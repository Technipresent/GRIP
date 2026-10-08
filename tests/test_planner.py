from grip.contracts import Claim
from grip.planner import plan


def test_main_claim_goes_to_both_providers():
    q = plan(Claim(id="c", text="Aspirin thins blood", subject="Aspirin"))
    main = [p for p in q if p.purpose == "claim"][0]
    assert main.text == "Aspirin thins blood"
    assert set(main.providers) == {"brave", "exa"}


def test_earlier_and_alternatives_go_to_exa():
    q = plan(Claim(id="c", text="Aspirin thins blood", subject="Aspirin"))
    purposes = {p.purpose: p for p in q}
    assert purposes["earlier"].providers == ("exa",)
    assert purposes["alternatives"].providers == ("exa",)


def test_numbers_and_dates_get_exact_query_on_brave():
    q = plan(Claim(id="c", text="Everest is 8849 metres tall", subject="Mount Everest"))
    exact = [p for p in q if p.purpose == "exact"]
    assert exact and exact[0].providers == ("brave",)
    assert '"8849"' in exact[0].text


def test_plain_claim_has_no_exact_query():
    q = plan(Claim(id="c", text="Aspirin thins blood", subject="Aspirin"))
    assert not [p for p in q if p.purpose == "exact"]


def test_plan_is_deterministic():
    c = Claim(id="c", text="Everest is 8849 metres tall", subject="Mount Everest")
    assert plan(c) == plan(c)
