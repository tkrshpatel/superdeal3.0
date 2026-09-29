"""Telegram ingestion adapter for SuperDeal 3.0.

Phase 3 keeps Telegram access behind a tiny interface so CI does not need
Telegram credentials. A real client can later implement TelegramSource.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    channel: str
    message_id: str
    text: str
    observed_at: str


class TelegramSource(Protocol):
    def fetch_messages(self, channel: str, *, limit: int = 100) -> Iterable[TelegramMessage]:
        ...


class MockTelegramSource:
    """Deterministic source used by tests and local development."""

    def __init__(self, messages: Iterable[TelegramMessage] = ()) -> None:
        self._messages = list(messages)

    def fetch_messages(self, channel: str, *, limit: int = 100) -> list[TelegramMessage]:
        if limit < 1:
            return []
        return [message for message in self._messages if message.channel == channel][:limit]
