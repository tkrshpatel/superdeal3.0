from superdeal.database import connect, get_deal, upsert_deal


def test_schema_and_first_insert():
    db = connect(":memory:")
    deal_id = upsert_deal(
        db,
        duplicate_hash="abc",
        product_name="BOLTT EVO",
        deal_price=8999,
        merchant="Flipkart",
        source_url="https://fkrt.to/a",
        raw_text="BOLTT EVO ₹8,999",
        observed_at="2026-09-30T00:00:00Z",
        source_channel="channel_a",
        source_message_id="1",
    )
    deal = get_deal(db, deal_id)
    assert deal["product_name"] == "BOLTT EVO"
    assert deal["current_price"] == 8999


def test_duplicate_observations_share_one_canonical_deal():
    db = connect(":memory:")
    kwargs = dict(
        duplicate_hash="same",
        product_name="BOLTT EVO",
        deal_price=8999,
        merchant="Flipkart",
        raw_text="BOLTT EVO ₹8,999",
        observed_at="2026-09-30T00:00:00Z",
    )
    first = upsert_deal(db, source_url="https://fkrt.to/a",
                        source_channel="channel_a", source_message_id="1", **kwargs)
    second = upsert_deal(db, source_url="https://fkrt.to/b",
                         source_channel="channel_b", source_message_id="2",
                         observed_at="2026-09-30T00:01:00Z", **{**kwargs, "raw_text": "SALE BOLTT EVO ₹8,999"})
    assert first == second
    assert db.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM source_observations").fetchone()[0] == 2


def test_price_history_only_records_price_changes():
    db = connect(":memory:")
    kwargs = dict(
        duplicate_hash="p1", product_name="Phone", merchant="Amazon",
        source_url="https://amzn.to/a", raw_text="Phone", source_channel="c",
    )
    upsert_deal(db, deal_price=1000, observed_at="2026-09-30T00:00:00Z",
                source_message_id="1", **kwargs)
    upsert_deal(db, deal_price=1000, observed_at="2026-09-30T01:00:00Z",
                source_message_id="2", **kwargs)
    upsert_deal(db, deal_price=900, observed_at="2026-09-30T02:00:00Z",
                source_message_id="3", **kwargs)
    rows = db.execute("SELECT price FROM price_history ORDER BY id").fetchall()
    assert [r[0] for r in rows] == [1000, 900]


def test_database_url_style_is_supported(tmp_path):
    path = tmp_path / "db" / "superdeal.db"
    db = connect(f"sqlite:///{path}")
    assert db.execute("SELECT 1").fetchone()[0] == 1
