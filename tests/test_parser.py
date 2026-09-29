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


def test_parses_atomberg_short_link():
    deal = parse_deal(
        """🔥 Lowest : atomberg Efficio Exhaust Fan 200mm (8 Inches) | BLDC Motor

Deal @ 1499 Only

https://amzn.to/4dfDtuG"""
    )
    assert deal.deal_price == 1499
    assert deal.merchant == "Amazon"


def test_parses_product_with_bank_offer():
    deal = parse_deal(
        """📱 New Launch : OPPO K14 Plus 5G
Deal @ 26000
✔️ Rs.4000 off with multiple cards
https://fkrt.to/514Sx0kH"""
    )
    assert deal.product_name == "New Launch : OPPO K14 Plus 5G"
    assert deal.deal_price == 26000
    assert deal.merchant == "Flipkart"
    assert any(p.type == "bank_offer" and p.value == 4000 for p in deal.promotions)


def test_parses_discount_range():
    deal = parse_deal(
        "🔥 85 to 90% Off https://fkrt.to/McPcWX13\n10 days return policy"
    )
    assert deal.discount_min_pct == 85
    assert deal.discount_max_pct == 90
    assert deal.deal_price is None
    assert deal.merchant == "Flipkart"


def test_parses_multi_link_campaign():
    deal = parse_deal(
        """🔥 Flipkart Fashion Fest
Ethnic Sets Flat ₹299 https://fkrt.to/rnxW1nLk
Festive Ethnic Sets Flat ₹399 https://fkrt.to/zhTv91nF
Kanjivaram, Banarasi sarees Flat ₹499 https://fkrt.to/T5Aj666B
Lehenga Cholis Flat ₹599 https://fkrt.to/ndF841WL
Anarkali Kurtis Flat ₹299 https://fkrt.to/52r0Grc6
Ready to wear Sarees min 70% Off https://fkrt.to/C1zASBP8"""
    )
    assert deal.deal_type == "campaign"
    assert deal.merchant == "Flipkart"
    assert len(deal.links) == 6
    assert deal.campaign == "Flipkart Fashion Fest"


def test_parses_stacked_offer():
    deal = parse_deal(
        """🔥 Triple Loot Offer On NIKE
+ 49% Off On MRP
+ Extra 20% Off On Buying 3
+ Extra 10% Off On ICICI/AXIS Credit cards
Add Any 3 to 5 Pair Shoes
https://fkrt.to/w5JVsWdJ"""
    )
    assert deal.brand == "NIKE"
    assert deal.discount_min_pct == 49
    assert deal.promotions
    assert any(p.type == "extra_discount" and p.value == 20 for p in deal.promotions)
    assert any(p.type == "extra_discount" and p.value == 10 for p in deal.promotions)


def test_parses_subscription_price():
    deal = parse_deal(
        """🔥 Presto! Ultra Strong Disinfectant Toilet Cleaner 5L
Deal @ 341 or 359
Use subscribe and save to get @ 341
https://amzn.to/3T5vz08"""
    )
    assert deal.deal_price == 341
    assert deal.merchant == "Amazon"
    assert any(p.type == "subscription_price" for p in deal.promotions)


def test_parses_brand_category_sale():
    deal = parse_deal(
        """🔥 Min. 70% off on Pepe Jeans Clothing.
Men’s : https://amzn.to/4zmFJsL
Women’s : https://amzn.to/3To199t"""
    )
    assert deal.discount_min_pct == 70
    assert deal.brand == "Pepe Jeans"
    assert deal.merchant == "Amazon"
    assert len(deal.links) == 2


def test_parses_product_and_cashback():
    deal = parse_deal(
        """📱 Sale Price Live : OnePlus Pad 2 (12.1 Inch),12GB RAM, 256GB Storage
Deal @29,699
Flat ₹2,000 off with SBI Debit & Credit Card + ₹300 Cashback
https://www.amazon.in/dp/B0D7N23QKD?th=1&tag=ganeshji00-21"""
    )
    assert deal.deal_price == 29699
    assert deal.brand == "OnePlus"
    assert deal.merchant == "Amazon"
    assert any(p.type == "bank_offer" and p.value == 2000 for p in deal.promotions)
    assert any(p.type == "cashback" and p.value == 300 for p in deal.promotions)


def test_parses_coupon_campaign():
    deal = parse_deal(
        """📱 Claim Rs.500 off coupon for Flipkart BBD sale
https://fkrt.to/G1A4KHgm
Valid for limited time."""
    )
    assert deal.deal_type == "coupon"
    assert deal.merchant == "Flipkart"
    assert any(p.type == "coupon" and p.value == 500 for p in deal.promotions)


def test_parses_reward_campaign():
    deal = parse_deal(
        """🔥🚨 Flipkart 120 Supercoin Today
Complete simple task like add to cart or Wishlist
👉 https://fkrt.to/mkh5KpJQ
Watch Video in Hindi
👉 https://youtu.be/YXL4dgcHW0c"""
    )
    assert deal.deal_type == "reward"
    assert deal.merchant == "Flipkart"
    assert len(deal.links) == 2


def test_boltt_variants_have_same_duplicate_identity():
    first = parse_deal(
        """🔥🚨 BOLTT EVO SALE IS LIVE!
💥 BOLTT EVO — ₹8,999 Effectively
🔋 6000mAh Battery
📱 6.79” Large Display
https://fkrt.to/M8bpYycf"""
    )
    second = parse_deal(
        """🔥 BOLTT EVO — EXCLUSIVE DEAL!
📱 Get BOLTT EVO at just ₹8,999*
💥 Price inclusive of ₹1,000 click coupon
💳 Extra 5% OFF on Flipkart Axis Bank & Flipkart SBI Credit Cards!
🔋 6000mAh Battery 📱 6.79” Large Display
https://fkrt.to/46DZfWw8"""
    )
    assert duplicate_hash(first) == duplicate_hash(second)


def test_duplicate_hash_ignores_url_and_wording():
    first = parse_deal("Bottle\nDeal @ 499\nhttps://example.com/a")
    second = parse_deal("🔥 Bottle\n₹499\nhttps://example.com/b")
    assert duplicate_hash(first) == duplicate_hash(second)


def test_requires_non_empty_text():
    with pytest.raises(ValueError):
        parse_deal("   ")
