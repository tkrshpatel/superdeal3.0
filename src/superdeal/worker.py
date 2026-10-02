"""Continuous Telegram ingestion orchestration."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable

from .database import connect
from .ingest import ingest_messages
from .telegram import TelegramBotSource
from .telegram_user import TelegramUserSource

LOGGER = logging.getLogger("superdeal.worker")


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    token: str
    channels: tuple[str, ...]
    database_url: str = "data/superdeal.db"
    poll_interval: float = 1.0
    batch_limit: int = 100
    reader_mode: str = "bot"
    api_id: str = ""
    api_hash: str = ""
    session: str = "data/telegram_user"

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        channels = tuple(item.strip() for item in os.getenv("TELEGRAM_CHANNELS", "").split(",") if item.strip())
        database_url = os.getenv("DATABASE_URL", "data/superdeal.db")
        poll_interval = float(os.getenv("TELEGRAM_POLL_INTERVAL", "1"))
        batch_limit = int(os.getenv("TELEGRAM_BATCH_LIMIT", "100"))
        reader_mode = os.getenv("TELEGRAM_READER_MODE", "bot").strip().lower()
        api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        session = os.getenv("TELEGRAM_SESSION", "data/telegram_user").strip()
        return cls(token, channels, database_url, poll_interval, batch_limit, reader_mode, api_id, api_hash, session)

    def validate(self) -> None:
        if self.reader_mode not in {"bot", "user"}:
            raise ValueError("TELEGRAM_READER_MODE must be 'bot' or 'user'")
        if self.reader_mode == "bot" and not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required in bot reader mode")
        if self.reader_mode == "user":
            if not self.api_id:
                raise ValueError("TELEGRAM_API_ID is required in user reader mode")
            if not self.api_hash:
                raise ValueError("TELEGRAM_API_HASH is required in user reader mode")
        if not self.channels:
            raise ValueError("TELEGRAM_CHANNELS must contain at least one channel")
        if self.poll_interval < 0:
            raise ValueError("TELEGRAM_POLL_INTERVAL must be non-negative")
        if not 1 <= self.batch_limit <= 100:
            raise ValueError("TELEGRAM_BATCH_LIMIT must be between 1 and 100")


def build_source(config: WorkerConfig):
    if config.reader_mode == "user":
        return TelegramUserSource(config.api_id, config.api_hash, session=config.session)
    return TelegramBotSource(config.token)


def run_once(config: WorkerConfig, *, source=None) -> int:
    config.validate()
    telegram = source or build_source(config)
    connection = connect(config.database_url, check_same_thread=False)
    try:
        messages_by_channel = telegram.fetch_messages_for_channels(config.channels, limit=config.batch_limit)
        received = sum(len(messages) for messages in messages_by_channel.values())
        LOGGER.info("Telegram %s reader received %d message(s) across %d configured channel(s)", config.reader_mode, received, len(config.channels))
        processed = sum(ingest_messages(connection, messages_by_channel.get(channel, [])) for channel in config.channels)
        LOGGER.info("Telegram poll ingested %d deal(s)", processed)
        return processed
    finally:
        connection.close()


def run_forever(config: WorkerConfig, *, source=None, sleep: Callable[[float], None] = time.sleep) -> None:
    config.validate()
    telegram = source or build_source(config)
    try:
        while True:
            try:
                run_once(config, source=telegram)
            except Exception:
                LOGGER.exception("Telegram polling cycle failed; retrying")
            sleep(config.poll_interval)
    finally:
        close = getattr(telegram, "close", None)
        if close:
            close()
