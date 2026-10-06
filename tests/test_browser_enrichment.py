from superdeal import browser_enrichment
from superdeal.web_enrichment import WebMetadata


def test_browser_first_returns_browser_metadata(monkeypatch):
    expected = WebMetadata(image_url="https://merchant.example/image.jpg")
    monkeypatch.setattr(browser_enrichment, "fetch_browser_metadata", lambda url: expected)

    def fail_http(url):
        raise AssertionError("HTTP fallback should not run")

    monkeypatch.setattr(browser_enrichment, "fetch_web_metadata", fail_http)
    assert browser_enrichment.fetch_product_metadata("https://earnkaro.example/x") == expected


def test_browser_failure_uses_existing_http_fallback(monkeypatch):
    def fail_browser(url):
        raise RuntimeError("browser unavailable")

    expected = WebMetadata(image_url="https://fallback.example/image.jpg")
    monkeypatch.setattr(browser_enrichment, "fetch_browser_metadata", fail_browser)
    monkeypatch.setattr(browser_enrichment, "fetch_web_metadata", lambda url: expected)

    assert browser_enrichment.fetch_product_metadata("https://earnkaro.example/x") == expected


def test_empty_browser_result_uses_existing_http_fallback(monkeypatch):
    monkeypatch.setattr(browser_enrichment, "fetch_browser_metadata", lambda url: WebMetadata())
    expected = WebMetadata(title="Fallback title", image_url="https://fallback.example/image.jpg")
    monkeypatch.setattr(browser_enrichment, "fetch_web_metadata", lambda url: expected)

    assert browser_enrichment.fetch_product_metadata("https://earnkaro.example/x") == expected
