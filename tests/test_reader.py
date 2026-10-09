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


def test_block_elements_become_sentence_boundaries():
    html = "<div>Home About Contact</div><p>Everest is 8,849 m tall</p><li>Next item</li>"
    assert "Everest is 8,849 m tall" in split_sentences(html_to_text(html))


async def test_reader_decodes_utf8_without_charset_header():
    body = "<p>The world’s tallest peak.</p>".encode("utf-8")
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=body, headers={"content-type": "text/html"})))
    assert await DirectReader(client).read("https://a.org") == "The world’s tallest peak."
