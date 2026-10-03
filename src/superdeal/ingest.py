"""Telegram ingestion: persist raw messages, then process only new exact payloads."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from .database import record_raw_telegram_message
from .parser import duplicate_hash, parse_deal
from .database import upsert_deal
from .telegram import TelegramMessage


def ingest_messages(connection: sqlite3.Connection, messages: Iterable[TelegramMessage]) -> int:
    """Persist every raw message; parse only messages that are not exact duplicates."""
    count = 0
    for message in messages:
        inserted = record_raw_telegram_message(
            connection,
            source_channel=message.channel,
            source_message_id=message.message_id,
            raw_text=message.text,
            observed_at=message.observed_at,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )

        if not inserted:
            continue

        raw_row = connection.execute(
            """SELECT is_duplicate FROM telegram_raw_messages
               WHERE source_channel = ? AND source_message_id = ?""",
            (message.channel, message.message_id),
        ).fetchone()

        if raw_row and int(raw_row["is_duplicate"]) == 1:
            continue

        deal = parse_deal(
            message.text,
            source_channel=message.channel,
            source_message_id=message.message_id,
        )
        upsert_deal(
            connection,
            duplicate_hash=duplicate_hash(deal),
            product_name=deal.product_name,
            deal_price=deal.deal_price,
            merchant=deal.merchant,
            source_url=deal.source_url,
            raw_text=deal.raw_text,
            observed_at=message.observed_at,
            source_channel=message.channel,
            source_message_id=message.message_id,
        )
        count += 1
    return count
