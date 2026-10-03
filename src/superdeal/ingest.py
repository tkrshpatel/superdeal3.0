"""Telegram-to-parser-to-database ingestion pipeline."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from .database import record_raw_telegram_message, upsert_deal
from .parser import duplicate_hash, parse_deal
from .telegram import TelegramMessage


def ingest_messages(connection: sqlite3.Connection, messages: Iterable[TelegramMessage]) -> int:
    """Persist raw Telegram messages first, then parse and persist deals."""
    count = 0
    for message in messages:
        # The raw ledger is committed before parsing so parser failures cannot
        # erase the original Telegram payload.
        record_raw_telegram_message(
            connection,
            source_channel=message.channel,
            source_message_id=message.message_id,
            raw_text=message.text,
            observed_at=message.observed_at,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )

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
