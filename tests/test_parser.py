import pytest

from superdeal.parser import duplicate_hash, parse_deal


def test_parses_common_telegram_format():
    message = """🔥 Noise Cancelling Headphones
MRP: ₹4,999
Deal Price: ₹1,999
60% OFF
https://www.amazon.in/dp/ABC123"""

    deal = parse_deal(message, source_channel="@deals", source_message_id="101")

    assert deal.product_name == "Noise Cancelling Headphones"
    assert deal.original_price == 4999
    assert deal.deal_price == 1999
    assert deal.discount_pct == 60
    assert deal.merchant == "Amazon"
    assert deal.source_channel == "@deals"
    assert deal.source_message_id == "101"


def test_infers_discount_when_not_written():
    deal = parse_deal("Kitchen Mixer\n₹2,499 → ₹1,499\nhttps://www.flipkart.com/item")

    assert deal.original_price == 2499
    assert deal.deal_price == 1499
    assert deal.discount_pct == 40
    assert deal.merchant == "Flipkart"


def test_handles_rs_and_unknown_merchant():
    deal = parse_deal("Wireless Mouse\nWas Rs. 999\nNow Rs 399\nhttps://example.com/deal")

    assert deal.product_name == "Wireless Mouse"
    assert deal.original_price == 999
    assert deal.deal_price == 399
    assert deal.discount_pct == 60
    assert deal.merchant is None


def test_parses_at_price_and_amazon_short_link():
    message = """🔥 Lowest : atomberg Efficio Exhaust Fan 200mm (8 Inches) | BLDC Motor

Deal @ 1499 Only

https://amzn.to/4dfDtuG"""

    deal = parse_deal(message)

    assert deal.product_name == "Lowest : atomberg Efficio Exhaust Fan 200mm (8 Inches) | BLDC Motor"
    assert deal.original_price is None
    assert deal.deal_price == 1499
    assert deal.discount_pct is None
    assert deal.merchant == "Amazon"
    assert deal.source_url == "https://amzn.to/4dfDtuG"


def test_parses_multi_product_coupon_message():
    message = """📱 Collect Rs.250 off on OPPO & HMD Mobiles for BBD Sale👇👇

Collect in Multiple Accounts

Oppo
👉 https://fkrt.to/55GPwG89

HMD
👉 https://fkrt.to/T7F6nXSk"""

    deal = parse_deal(message)

    assert deal.product_name == "Collect Rs.250 off on OPPO & HMD Mobiles for BBD Sale"
    assert deal.original_price is None
    assert deal.deal_price is None
    assert deal.discount_pct is None
    assert deal.merchant == "Flipkart"
    assert deal.source_url == "https://fkrt.to/55GPwG89"


def test_requires_non_empty_text():
    with pytest.raises(ValueError):
        parse_deal("   ")


def test_duplicate_hash_is_stable():
    first = parse_deal("Bottle\n₹999 → ₹499")
    second = parse_deal("Bottle\nMRP ₹999\nDeal Price ₹499")

    assert duplicate_hash(first) == duplicate_hash(second)
