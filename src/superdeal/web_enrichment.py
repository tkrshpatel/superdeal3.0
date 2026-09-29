"""Credential-free web metadata enrichment for deal URLs."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin


@dataclass(frozen=True, slots=True)
class WebMetadata:
    title: str | None = None
    canonical_url: str | None = None
    image_url: str | None = None
    price: int | None = None


class _MetadataParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.metadata: dict[str, str] = {}
        self._title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content")
            if key and content:
                self.metadata[key] = content.strip()
        if tag == "link" and (values.get("rel") or "").lower() == "canonical" and values.get("href"):
            self.metadata["canonical"] = urljoin(self.base_url, values["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip():
            self._title_parts.append(data.strip())


def _price(value: str | None) -> int | None:
    if not value:
        return None
    import re
    match = re.search(r"(?:₹|INR|Rs\.?)[\s]*([\d,]+)", value, re.I)
    if not match:
        match = re.search(r"\b([1-9]\d{2,6})\b", value)
    return int(match.group(1).replace(",", "")) if match else None


def parse_html_metadata(html: str, *, source_url: str) -> WebMetadata:
    parser = _MetadataParser(source_url)
    parser.feed(html)
    title = " ".join(parser._title_parts).strip() or parser.metadata.get("og:title")
    image = parser.metadata.get("og:image")
    if image:
        image = urljoin(source_url, image)
    return WebMetadata(
        title=title[:500] if title else None,
        canonical_url=parser.metadata.get("canonical") or parser.metadata.get("og:url"),
        image_url=image,
        price=_price(parser.metadata.get("product:price:amount") or parser.metadata.get("og:price:amount")),
    )


def fetch_web_metadata(url: str, *, timeout: float = 5.0) -> WebMetadata:
    """Fetch lightweight public HTML metadata. No login or provider API is used."""
    request = Request(url, headers={"User-Agent": "SuperDealBot/1.0 (+deal metadata)"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return WebMetadata()
        html = response.read(1_000_000).decode("utf-8", errors="replace")
    return parse_html_metadata(html, source_url=url)
