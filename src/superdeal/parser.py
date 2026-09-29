"""Deterministic parsing utilities for common Telegram deal messages.

The parser intentionally preserves information rather than trying to make
business decisions about the effective price of a promotion.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse


PRICE_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)
PLAIN_PRICE_RE = re.compile(
    r"(?:deal\s*@|offer\s*@|now\s*@|price\s*@|@)\s*₹?\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
DISCOUNT_RE = re.compile(
    r"(\d{1,3})\s*(?:to\s*(\d{1,3})\s*)?%\s*(?:off|discount)",
    re.IGNORECASE,
)
MIN_DISCOUNT_RE = re.compile(
    r"(?:min(?:imum)?\.?\s*)?(\d{1,3})\s*%\s*off",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
BRAND_RE = re.compile(r"\b(?:on|from)\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+){0,3})", re.IGNORECASE)
CARD_RE = re.compile(
    r"((?:ICICI|AXIS|SBI|HDFC|Kotak|Flipkart Axis|Flipkart SBI)(?:[^\n]*?)(?:credit|debit)?\s*cards?)",
    re.IGNORECASE,
)

KNOWN_MERCHANTS = {
    "amazon.in": "Amazon",
    "amazon.com": "Amazon",
    "amzn.to": "Amazon",
    "flipkart.com": "Flipkart",
    "fkrt.to": "Flipkart",
    "myntra.com": "Myntra",
    "ajio.com": "AJIO",
    "meesho.com": "Meesho",
    "croma.com": "Croma",
    "tatacliq.com": "Tata CLiQ",
    "nykaa.com": "Nykaa",
}


@dataclass(slots=True)
class DealLink:
    url: str
    label: str | None = None
    link_type: str = "source"


@dataclass(slots=True)
class Promotion:
    type: str
    value: int | float | str | None = None
    condition: str | None = None
    merchant: str | None = None
    payment_method: str | None = None


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

    # Phase 1 normalized fields.
    deal_type: str = "product"
    discount_min_pct: int | None = None
    discount_max_pct: int | None = None
    face_value: int | None = None
    brand: str | None = None
    campaign: str | None = None
    links: list[DealLink] = field(default_factory=list)
    promotions: list[Promotion] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _price_value(value: str) -> int:
    return int(round(float(value.replace(",", ""))))


def _clean_url(url: str) -> str:
    return url.rstrip(".,;!?)\\]}>\"'")


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


def _extract_discount(text: str) -> tuple[int | None, int | None]:
    match = DISCOUNT_RE.search(text)
    if not match:
        return None, None
    low = int(match.group(1))
    high = int(match.group(2) or low)
    return low, high


def _extract_urls(text: str) -> list[str]:
    return [_clean_url(url) for url in URL_RE.findall(text)]


def _url_labels(text: str) -> list[DealLink]:
    links: list[DealLink] = []
    for line in text.splitlines():
        urls = URL_RE.findall(line)
        if not urls:
            continue
        label = line
        for url in urls:
            clean = _clean_url(url)
            label = label.replace(url, "").strip(" :-👉")
            links.append(DealLink(url=clean, label=label or None))
    return links


def _product_name(text: str) -> str:
    for line in text.splitlines():
        cleaned = re.sub(r"https?://\S+", "", line).strip()
        cleaned = re.sub(r"^[\s\W_]+", "", cleaned).strip()
        if not cleaned:
            continue
        if re.search(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+|(?:deal\s*@|offer\s*@|now\s*@)\s*₹?\s*[\d,]+|\d+\s*%\s*(?:off|discount)",
            cleaned,
            re.I,
        ):
            continue
        if re.fullmatch(
            r"(buy\s+now|shop\s+now|get\s+it|click\s+here)\W*", cleaned, re.I
        ):
            continue
        return cleaned[:240]
    return "Unknown product"


def _classify(text: str, product_name: str) -> str:
    lower = text.lower()
    if "supercoin" in lower or "supercoin" in product_name.lower():
        return "reward"
    if "gift voucher" in lower or "gift card" in lower:
        return "gift_voucher"
    if "coupon" in lower and not re.search(r"\bdeal\s*@", lower):
        return "coupon"
    if any(term in lower for term in ("fashion fest", "sale", "campaign")) and not re.search(r"\bdeal\s*@", lower):
        return "campaign"
    if "cashback" in lower and not re.search(r"\bdeal\s*@", lower):
        return "promotion"
    return "product"


def _extract_brand(text: str) -> str | None:
    for known in ("NIKE", "Pepe Jeans", "BOLTT", "OnePlus", "OPPO", "Tecno", "Infinix", "Lava"):
        if re.search(rf"\b{re.escape(known)}\b", text, re.IGNORECASE):
            return known
    return None


def _extract_campaign(text: str) -> str | None:
    for pattern in (
        r"([A-Za-z0-9&' -]+(?:Fashion Fest|BBD(?: Sale)?|Sale))",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" -:")
    return None


def _extract_promotions(text: str) -> list[Promotion]:
    promotions: list[Promotion] = []
    for line in text.splitlines():
        lower = line.lower()
        if "coupon" in lower:
            match = re.search(r"(?:rs\.?|₹)\s*([\d,]+)\s*off", line, re.I)
            if match:
                promotions.append(Promotion("coupon", _price_value(match.group(1)), line.strip()))
        if "cashback" in lower:
            amount = re.search(r"(?:rs\.?|₹)\s*([\d,]+)", line, re.I)
            pct = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
            value: int | float | str | None = None
            if amount:
                value = _price_value(amount.group(1))
            elif pct:
                value = float(pct.group(1)) if "." in pct.group(1) else int(pct.group(1))
            promotions.append(Promotion("cashback", value, line.strip()))
        if re.search(r"extra\s+\d+\s*%", lower):
            pct = re.search(r"extra\s+(\d+)\s*%", lower)
            if pct:
                payment = "card" if "card" in lower else None
                promotions.append(Promotion("extra_discount", int(pct.group(1)), line.strip(), payment_method=payment))
        if "subscribe and save" in lower or "subscription" in lower:
            promotions.append(Promotion("subscription_price", None, line.strip()))
    return promotions


def parse_deal(
    text: str,
    *,
    source_channel: str | None = None,
    source_message_id: str | None = None,
) -> Deal:
    """Parse common deal-message structures without an LLM or network access."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Deal message must be a non-empty string.")

    urls = _extract_urls(text)
    source_url = urls[0] if urls else None

    original_price = _extract_labelled_price(text, ("MRP", "Original", "Was", "Before"))
    deal_price = _extract_labelled_price(text, ("Deal Price", "Offer Price", "Now", "Price"))

    plain_prices = [_price_value(m.group(1)) for m in PLAIN_PRICE_RE.finditer(text)]
    if deal_price is None and plain_prices:
        # "Deal @ 341 or 359" means the first advertised deal price.
        deal_price = plain_prices[0]

    prices = [_price_value(m.group(1)) for m in PRICE_RE.finditer(text)]
    if deal_price is None and prices:
        # For a simple product message, a single explicit price is the deal price.
        deal_price = prices[-1]

    if original_price is None and len(prices) >= 2:
        candidates = [p for p in prices if p != deal_price]
        if candidates:
            original_price = max(candidates)

    discount_min, discount_max = _extract_discount(text)
    discount_pct = discount_min
    if discount_pct is None and original_price and deal_price and original_price > deal_price:
        discount_pct = round((original_price - deal_price) / original_price * 100)
        discount_min = discount_max = discount_pct

    product_name = _product_name(text)
    deal_type = _classify(text, product_name)
    links = _url_labels(text)
    merchant = _merchant_from_url(source_url)
    brand = _extract_brand(text)
    campaign = _extract_campaign(text)

    # A "deal @ price" is a product even when marketing copy contains "sale".
    if re.search(r"\bdeal\s*@", text, re.I):
        deal_type = "product"

    return Deal(
        product_name=product_name,
        original_price=original_price,
        deal_price=deal_price,
        discount_pct=discount_pct,
        merchant=merchant,
        source_url=source_url,
        source_channel=source_channel,
        source_message_id=source_message_id,
        raw_text=text,
        deal_type=deal_type,
        discount_min_pct=discount_min,
        discount_max_pct=discount_max,
        brand=brand,
        campaign=campaign,
        links=links,
        promotions=_extract_promotions(text),
    )


def _duplicate_product_key(product_name: str) -> str:
    """Normalize obvious marketing language before duplicate matching."""
    value = product_name.lower()
    value = re.sub(r"\b(?:sale|deal|offer|exclusive|live|today|is|the|wait|over|now)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def duplicate_hash(deal: Deal) -> str:
    """Return a stable basic identity hash for duplicate detection.

    URLs and raw message text are deliberately excluded: different Telegram
    channels often publish the same deal with different links and wording.
    """
    product = _duplicate_product_key(deal.product_name)
    key = "|".join(
        [
            (deal.merchant or "").lower().strip(),
            product,
            str(deal.deal_price or ""),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
