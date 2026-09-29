from superdeal.database import connect
from superdeal.ingest import ingest_messages
from superdeal.telegram import MockTelegramSource, TelegramMessage


def test_mock_source_filters_channel_and_limit():
    source = MockTelegramSource([
        TelegramMessage("deals_a", "1", "BOLTT EVO Deal @ 8999 https://fkrt.to/a", "2026-09-30T00:00:00Z"),
        TelegramMessage("deals_b", "2", "Other Deal @ 499 https://amzn.to/b", "2026-09-30T00:01:00Z"),
        TelegramMessage("deals_a", "3", "Another Deal @ 999 https://amzn.to/c", "2026-09-30T00:02:00Z"),
    ])
    assert [m.message_id for m in source.fetch_messages("deals_a", limit=1)] == ["1"]


def test_ingest_parses_and_persists_message():
    db = connect(":memory:")
    message = TelegramMessage("deals_a", "42", "BOLTT EVO Deal @ 8999 https://fkrt.to/a", "2026-09-30T00:00:00Z")
    assert ingest_messages(db, [message]) == 1
    row = db.execute("SELECT * FROM deals").fetchone()
    assert row["product_name"] == "BOLTT EVO"
    assert row["current_price"] == 8999
    assert row["merchant"] == "Flipkart"
    observation = db.execute("SELECT * FROM source_observations").fetchone()
    assert observation["source_channel"] == "deals_a"
    assert observation["source_message_id"] == "42"


def test_duplicate_messages_from_multiple_channels_share_canonical_deal():
    db = connect(":memory:")
    messages = [
        TelegramMessage("deals_a", "1", "BOLTT EVO Deal @ 8999 https://fkrt.to/a", "2026-09-30T00:00:00Z"),
        TelegramMessage("deals_b", "9", "BOLTT EVO Deal @ 8999 https://fkrt.to/b", "2026-09-30T00:01:00Z"),
    ]
    assert ingest_messages(db, messages) == 2
    assert db.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM source_observations").fetchone()[0] == 2
