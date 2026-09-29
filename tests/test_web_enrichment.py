from superdeal.web_enrichment import parse_html_metadata


def test_parse_product_metadata():
    html = """
    <html><head>
      <title>Atomberg Efficio Exhaust Fan</title>
      <meta property="og:title" content="Atomberg Efficio Exhaust Fan 200mm">
      <meta property="og:image" content="/images/fan.jpg">
      <meta property="og:url" content="https://example.com/product/fan">
      <meta property="product:price:amount" content="1499">
      <link rel="canonical" href="https://example.com/product/fan?ref=deal">
    </head></html>
    """
    result = parse_html_metadata(html, source_url="https://example.com/deal")
    assert result.title == "Atomberg Efficio Exhaust Fan"
    assert result.image_url == "https://example.com/images/fan.jpg"
    assert result.canonical_url == "https://example.com/product/fan?ref=deal"
    assert result.price == 1499


def test_missing_metadata_is_safe():
    result = parse_html_metadata("<html><body>Nothing useful</body></html>", source_url="https://example.com")
    assert result == result.__class__()
