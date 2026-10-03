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


def test_ingest_stores_exact_original_message_without_parsing():
    db = connect(":memory:")
    original = """🔥 Men Printed Kurta (Orange) @ ₹244

🔗 https://bitli.in/gG4FnEe"""
    message = TelegramMessage("deals_a", "42", original, "2026-09-30T00:00:00Z")

    assert ingest_messages(db, [message]) == 1
    row = db.execute(
        """SELECT source_channel, telegram_message_id, telegram_message_timestamp,
                  ingested_at, original_message_text
           FROM telegram_raw_messages"""
    ).fetchone()

    assert row["source_channel"] == "deals_a"
    assert row["telegram_message_id"] == "42"
    assert row["telegram_message_timestamp"] == "2026-09-30T00:00:00Z"
    assert row["ingested_at"]
    assert row["original_message_text"] == original
    assert db.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 0


def test_duplicate_telegram_message_is_not_inserted_twice():
    db = connect(":memory:")
    message = TelegramMessage("deals_a", "42", "anything at all", "2026-09-30T00:00:00Z")

    assert ingest_messages(db, [message]) == 1
    assert ingest_messages(db, [message]) == 0
    assert db.execute("SELECT COUNT(*) FROM telegram_raw_messages").fetchone()[0] == 1


def test_multiple_formats_are_stored_unchanged():
    db = connect(":memory:")
    messages = [
        TelegramMessage("deals_a", "1", "No price here, just a link https://example.com/a", "2026-09-30T00:00:00Z"),
        TelegramMessage("deals_b", "2", "Mens\nJeans: https://myntr.it/a\nWomens\nDresses: https://myntr.it/b", "2026-09-30T00:01:00Z"),
        TelegramMessage("deals_c", "3", "🛍️ 完全 unexpected format !!!", "2026-09-30T00:02:00Z"),
    ]

    assert ingest_messages(db, messages) == 3
    rows = db.execute(
        "SELECT source_channel, telegram_message_id, original_message_text "
        "FROM telegram_raw_messages ORDER BY id"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("deals_a", "1", messages[0].text),
        ("deals_b", "2", messages[1].text),
        ("deals_c", "3", messages[2].text),
    ]
