"""Page reading: fetch a page and reduce it to plain sentences."""
import re
from html.parser import HTMLParser

import httpx


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"\s+", " ", "".join(p.parts)).strip()


_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if s.strip()]


class DirectReader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def read(self, url: str) -> str:
        r = await self.client.get(url, timeout=20, follow_redirects=True,
                                  headers={"User-Agent": "GRIP-Grounding/2.0"})
        r.raise_for_status()
        return html_to_text(r.text)
