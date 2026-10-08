import httpx

from grip.reader import DirectReader, html_to_text, split_sentences


def test_html_to_text_drops_scripts_and_tags():
    html = "<html><script>x=1</script><p>Aspirin <b>reduces</b> pain.</p><style>p{}</style></html>"
    assert html_to_text(html) == "Aspirin reduces pain."


def test_split_sentences():
    assert split_sentences("A is B. C is D! E?") == ["A is B.", "C is D!", "E?"]


async def test_direct_reader_fetches_and_cleans():
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, text="<p>Hello world.</p>")))
    assert await DirectReader(client).read("https://a.org") == "Hello world."
