import httpx
import pytest

from grip.providers.base import ProviderError
from grip.providers.brave import BraveProvider
from grip.providers.exa import ExaProvider


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_brave_parses_results_and_sends_key():
    def handler(request):
        assert request.headers["X-Subscription-Token"] == "k"
        assert request.url.params["q"] == "aspirin"
        return httpx.Response(200, json={"web": {"results": [
            {"url": "https://a.org/x", "title": "A", "description": "d"}]}})
    hits = await BraveProvider("k", _client(handler)).search("aspirin")
    assert [(h.url, h.provider) for h in hits] == [("https://a.org/x", "brave")]


async def test_exa_parses_results_and_sends_key():
    def handler(request):
        assert request.headers["x-api-key"] == "k"
        return httpx.Response(200, json={"results": [
            {"url": "https://b.org/y", "title": "B", "text": "t"}]})
    hits = await ExaProvider("k", _client(handler)).search("aspirin")
    assert [(h.url, h.provider) for h in hits] == [("https://b.org/y", "exa")]


@pytest.mark.parametrize("cls", [BraveProvider, ExaProvider])
async def test_provider_error_on_bad_status(cls):
    client = _client(lambda r: httpx.Response(500))
    with pytest.raises(ProviderError):
        await cls("k", client).search("q")


@pytest.mark.parametrize("cls", [BraveProvider, ExaProvider])
async def test_provider_error_on_missing_key(cls):
    with pytest.raises(ProviderError):
        await cls("", _client(lambda r: httpx.Response(200))).search("q")
