"""Utilities for turning common deal-message text into structured data."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse


PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
DISCOUNT_RE = re.compile(r"(\d{1,3})\s*%\s*(?:off|discount)", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)

KNOWN_MERCHANTS = {
    "amazon.in": "Amazon",
    "amazon.com": "Amazon",
    "flipkart.com": "Flipkart",
    "myntra.com": "Myntra",
    "ajio.com": "AJIO",
    "meesho.com": "Meesho",
    "croma.com": "Croma",
    "tatacliq.com": "Tata CLiQ",
    "nykaa.com": "Nykaa",
}


@dataclass(slots=True)
class Deal:
    product_name: str
    original_price: int | None = None
    deal_price: int | None = None
    discount_pct: int | None = None
    merchant: str | None = None
    source_url: str | None = None
    source_channel: str | None = None
    source_message_id: str | None = None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _price_value(value: str) -> int:
    return int(round(float(value.replace(",", ""))))


def _clean_url(url: str) -> str:
    return url.rstrip(".,;!?)\]}>"'")


def _merchant_from_url(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    for domain, merchant in KNOWN_MERCHANTS.items():
        if host == domain or host.endswith("." + domain):
            return merchant
    return None


def _extract_labelled_price(text: str, labels: tuple[str, ...]) -> int | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*[:=-]?\s*(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{{1,2}})?)",
        text,
        re.IGNORECASE,
    )
    return _price_value(match.group(1)) if match else None


def _product_name(text: str) -> str:
    for line in text.splitlines():
        cleaned = re.sub(r"https?://\S+", "", line).strip()
        cleaned = re.sub(r"^[\s\W_]+", "", cleaned).strip()
        if not cleaned:
            continue
        if re.search(r"(?:₹|Rs\.?|INR)\s*[\d,]+|\d+\s*%\s*(?:off|discount)", cleaned, re.I):
            continue
        if re.fullmatch(r"(buy\s+now|shop\s+now|get\s+it|click\s+here)\W*", cleaned, re.I):
            continue
        return cleaned[:240]
    return "Unknown product"


def parse_deal(
    text: str,
    *,
    source_channel: str | None = None,
    source_message_id: str | None = None,
) -> Deal:
    """Parse a deal message without requiring an LLM or network access."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Deal message must be a non-empty string.")

    urls = [_clean_url(u) for u in URL_RE.findall(text)]
    source_url = urls[0] if urls else None

    original_price = _extract_labelled_price(text, ("MRP", "Original", "Was", "Before"))
    deal_price = _extract_labelled_price(text, ("Deal Price", "Offer Price", "Now", "Price"))

    prices = [_price_value(m.group(1)) for m in PRICE_RE.finditer(text)]
    if deal_price is None and prices:
        deal_price = prices[-1]
    if original_price is None and len(prices) >= 2:
        candidates = [p for p in prices if p != deal_price]
        if candidates:
            original_price = max(candidates)

    discount_match = DISCOUNT_RE.search(text)
    discount_pct = int(discount_match.group(1)) if discount_match else None

    if discount_pct is None and original_price and deal_price and original_price > deal_price:
        discount_pct = round((original_price - deal_price) / original_price * 100)

    return Deal(
        product_name=_product_name(text),
        original_price=original_price,
        deal_price=deal_price,
        discount_pct=discount_pct,
        merchant=_merchant_from_url(source_url),
        source_url=source_url,
        source_channel=source_channel,
        source_message_id=source_message_id,
        raw_text=text,
    )


def duplicate_hash(deal: Deal) -> str:
    """Return a stable hash for basic duplicate detection."""
    key = "|".join(
        [
            deal.product_name.lower().strip(),
            str(deal.deal_price or ""),
            str(deal.merchant or "").lower().strip(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
