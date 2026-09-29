"""Telegram-to-parser-to-database ingestion pipeline."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from .database import upsert_deal
from .parser import duplicate_hash, parse_deal
from .telegram import TelegramMessage


def ingest_messages(connection: sqlite3.Connection, messages: Iterable[TelegramMessage]) -> int:
    """Parse and persist Telegram messages, returning processed message count."""
    count = 0
    for message in messages:
        deal = parse_deal(message.text, source_channel=message.channel, source_message_id=message.message_id)
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
