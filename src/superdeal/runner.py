"""Production-oriented entry points for the Telegram worker."""

from __future__ import annotations

import logging
import os

from .telegram import TelegramBotSource
from .worker import WorkerConfig, run_forever

LOGGER = logging.getLogger("superdeal.worker")


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def check_telegram(config: WorkerConfig) -> dict[str, object]:
    """Verify bot credentials and Telegram API access without ingesting messages."""
    config.validate()
    bot = TelegramBotSource(config.token)
    identity = bot.get_me()
    return {"ok": True, "bot": identity}


def main() -> None:
    configure_logging()
    config = WorkerConfig.from_env()
    LOGGER.info("Starting SuperDeal Telegram worker for %d channel(s)", len(config.channels))
    check_telegram(config)
    run_forever(config)


if __name__ == "__main__":
    main()
