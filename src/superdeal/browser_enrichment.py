"""Browser-backed product enrichment with the existing HTTP fetcher as fallback."""

from __future__ import annotations

import logging

from .web_enrichment import WebMetadata, fetch_web_metadata, parse_html_metadata

LOGGER = logging.getLogger("superdeal.browser_enrichment")


def _useful(metadata: WebMetadata) -> bool:
    return bool(metadata.image_url or metadata.description or metadata.brand or metadata.price or metadata.mrp)


def fetch_browser_metadata(url: str, *, timeout_ms: int = 15000) -> WebMetadata:
    """Follow an affiliate URL in Chromium and extract metadata from the rendered page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="en-IN",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
            except Exception:
                pass
            metadata = parse_html_metadata(page.content(), source_url=page.url)
            if metadata.canonical_url:
                return metadata
            return WebMetadata(
                title=metadata.title,
                description=metadata.description,
                brand=metadata.brand,
                canonical_url=page.url,
                image_url=metadata.image_url,
                price=metadata.price,
                mrp=metadata.mrp,
            )
        finally:
            browser.close()


def fetch_product_metadata(url: str) -> WebMetadata:
    """Prefer rendered-browser enrichment, falling back to the existing HTTP logic."""
    try:
        metadata = fetch_browser_metadata(url)
        if _useful(metadata):
            return metadata
        LOGGER.info("Browser enrichment returned no useful product fields; using HTTP fallback")
    except Exception as exc:
        LOGGER.warning("Browser enrichment failed; using HTTP fallback: %s", exc)
    return fetch_web_metadata(url)
