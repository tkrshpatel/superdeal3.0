"""Affiliate-ready URL handling without inventing provider APIs."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_source_url(url: str | None) -> str | None:
    """Normalize a source URL for stable storage and comparison."""
    if not url:
        return None
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source URL must be an absolute HTTP(S) URL")
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", parsed.query, "")
    )


def build_affiliate_url(source_url: str | None, affiliate_url: str | None = None) -> str | None:
    """Return an explicitly supplied affiliate URL, otherwise the normalized source URL.

    The fallback is intentionally the merchant/source URL. A real affiliate
    provider must be plugged in separately once its documented integration is verified.
    """
    if affiliate_url:
        return normalize_source_url(affiliate_url)
    return normalize_source_url(source_url)
