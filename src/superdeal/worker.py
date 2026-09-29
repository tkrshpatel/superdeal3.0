"""Continuous Telegram ingestion orchestration."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from .database import connect
from .ingest import ingest_messages
from .telegram import TelegramBotSource


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    token: str
    channels: tuple[str, ...]
    database_url: str = "data/superdeal.db"
    poll_interval: float = 1.0
    batch_limit: int = 100

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        channels = tuple(item.strip() for item in os.getenv("TELEGRAM_CHANNELS", "").split(",") if item.strip())
        database_url = os.getenv("DATABASE_URL", "data/superdeal.db")
        poll_interval = float(os.getenv("TELEGRAM_POLL_INTERVAL", "1"))
        batch_limit = int(os.getenv("TELEGRAM_BATCH_LIMIT", "100"))
        return cls(token, channels, database_url, poll_interval, batch_limit)

    def validate(self) -> None:
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.channels:
            raise ValueError("TELEGRAM_CHANNELS must contain at least one channel")
        if self.poll_interval < 0:
            raise ValueError("TELEGRAM_POLL_INTERVAL must be non-negative")
        if not 1 <= self.batch_limit <= 100:
            raise ValueError("TELEGRAM_BATCH_LIMIT must be between 1 and 100")


def run_once(config: WorkerConfig, *, source: TelegramBotSource | None = None) -> int:
    """Fetch and persist one batch from every configured channel."""
    config.validate()
    telegram = source or TelegramBotSource(config.token)
    connection = connect(config.database_url, check_same_thread=False)
    try:
        processed = 0
        for channel in config.channels:
            processed += ingest_messages(
                connection,
                telegram.fetch_messages(channel, limit=config.batch_limit),
            )
        return processed
    finally:
        connection.close()


def run_forever(
    config: WorkerConfig,
    *,
    source: TelegramBotSource | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Continuously ingest configured channels until the process is stopped."""
    config.validate()
    while True:
        run_once(config, source=source)
        sleep(config.poll_interval)
