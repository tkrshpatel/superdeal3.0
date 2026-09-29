"""Telegram ingestion adapters for SuperDeal 3.0."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


class TelegramAPIError(RuntimeError):
    """Raised when Telegram returns an unsuccessful Bot API response."""


class TelegramBotSource:
    """Read channel posts through Telegram Bot API long polling."""

    def __init__(self, token: str, *, timeout: int = 25, request: Callable[[str, dict], dict] | None = None) -> None:
        if not token.strip():
            raise ValueError("Telegram bot token is required")
        if timeout < 1:
            raise ValueError("timeout must be positive")
        self.token = token.strip()
        self.timeout = timeout
        self._request = request or self._http_request
        self._offset = 0

    def _http_request(self, method: str, params: dict) -> dict:
        query = urlencode(params)
        url = f"https://api.telegram.org/bot{self.token}/{method}?{query}"
        request = Request(url, headers={"User-Agent": "SuperDealBot/1.0"})
        with urlopen(request, timeout=self.timeout + 5) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_me(self) -> dict:
        return self._call("getMe", {})

    def fetch_updates(self, *, limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        updates = self._call("getUpdates", {
            "offset": self._offset or None,
            "limit": limit,
            "timeout": self.timeout,
            "allowed_updates": json.dumps(["channel_post", "edited_channel_post"]),
        })
        if updates:
            self._offset = max(int(item["update_id"]) for item in updates) + 1
        return updates

    def fetch_messages(self, channel: str, *, limit: int = 100) -> list[TelegramMessage]:
        if limit < 1:
            return []
        wanted = channel.lstrip("@").lower()
        messages: list[TelegramMessage] = []
        for update in self.fetch_updates(limit=min(limit, 100)):
            payload = update.get("channel_post") or update.get("edited_channel_post")
            if not payload:
                continue
            chat = payload.get("chat") or {}
            username = str(chat.get("username", "")).lstrip("@").lower()
            identifiers = {str(chat.get("id", "")), username, str(chat.get("title", "")).lower()}
            if wanted not in identifiers and channel not in identifiers:
                continue
            timestamp = datetime.fromtimestamp(int(payload["date"]), tz=timezone.utc).isoformat()
            text = payload.get("text") or payload.get("caption") or ""
            messages.append(TelegramMessage(channel=channel, message_id=str(payload["message_id"]), text=str(text), observed_at=timestamp))
        return messages

    def _call(self, method: str, params: dict) -> list | dict:
        cleaned = {key: value for key, value in params.items() if value is not None}
        payload = self._request(method, cleaned)
        if not payload.get("ok"):
            raise TelegramAPIError(payload.get("description", f"Telegram {method} failed"))
        return payload.get("result", [])
