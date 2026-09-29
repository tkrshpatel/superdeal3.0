"""SQLite persistence for SuperDeal 3.0.

Phase 2 keeps persistence deliberately small and dependency-free.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    duplicate_hash TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    merchant TEXT,
    current_price INTEGER,
    source_url TEXT,
    affiliate_url TEXT,
    raw_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    source_channel TEXT,
    source_message_id TEXT,
    source_url TEXT,
    raw_text TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE(source_channel, source_message_id)
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    observed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
CREATE INDEX IF NOT EXISTS idx_observations_deal ON source_observations(deal_id);
CREATE INDEX IF NOT EXISTS idx_price_history_deal ON price_history(deal_id);
"""


def connect(
    database_url: str | Path = "data/superdeal.db",
    *,
    check_same_thread: bool = True,
) -> sqlite3.Connection:
    """Open SQLite and initialize the schema."""
    path = str(database_url)
    if path.startswith("sqlite:///"):
        path = path[len("sqlite:///") :]
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=check_same_thread)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(deals)").fetchall()}
    if "affiliate_url" not in columns:
        connection.execute("ALTER TABLE deals ADD COLUMN affiliate_url TEXT")
        connection.commit()
    return connection


def upsert_deal(
    connection: sqlite3.Connection,
    *,
    duplicate_hash: str,
    product_name: str,
    deal_price: int | None,
    merchant: str | None,
    source_url: str | None,
    raw_text: str,
    affiliate_url: str | None = None,
    observed_at: str,
    source_channel: str | None = None,
    source_message_id: str | None = None,
) -> int:
    """Insert a deal or update its latest observation."""
    row = connection.execute(
        "SELECT id FROM deals WHERE duplicate_hash = ?",
        (duplicate_hash,),
    ).fetchone()

    if row:
        deal_id = int(row["id"])
        connection.execute(
            """UPDATE deals
               SET product_name = ?, merchant = ?, current_price = ?,
                   source_url = ?, affiliate_url = ?, raw_text = ?, last_seen_at = ?
               WHERE id = ?""",
            (product_name, merchant, deal_price, source_url, affiliate_url, raw_text, observed_at, deal_id),
        )
    else:
        cursor = connection.execute(
            """INSERT INTO deals
               (duplicate_hash, product_name, merchant, current_price,
                source_url, raw_text, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (duplicate_hash, product_name, merchant, deal_price, source_url, affiliate_url, raw_text,
             observed_at, observed_at),
        )
        deal_id = int(cursor.lastrowid)

    if source_channel is not None or source_message_id is not None:
        connection.execute(
            """INSERT OR IGNORE INTO source_observations
               (deal_id, source_channel, source_message_id, source_url, raw_text, observed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (deal_id, source_channel, source_message_id, source_url, raw_text, observed_at),
        )

    if deal_price is not None:
        latest = connection.execute(
            """SELECT price FROM price_history
               WHERE deal_id = ? ORDER BY id DESC LIMIT 1""",
            (deal_id,),
        ).fetchone()
        if latest is None or int(latest["price"]) != deal_price:
            connection.execute(
                "INSERT INTO price_history (deal_id, price, observed_at) VALUES (?, ?, ?)",
                (deal_id, deal_price, observed_at),
            )

    connection.commit()
    return deal_id


def get_deal(connection: sqlite3.Connection, deal_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    return dict(row) if row else None
