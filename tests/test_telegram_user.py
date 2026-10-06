from datetime import datetime, timezone

import pytest

from superdeal.telegram import TelegramMessage
from superdeal.telegram_user import (
    TelegramUserReaderError,
    TelegramUserSource,
    normalize_user_channel,
)


class FakeMessage:
    def __init__(self, message_id, text):
        self.id = message_id
        self.raw_text = text
        self.date = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


class FakeEntity:
    username = "amazinglootsdealsoffers"
    title = "Amazing Loots Deals Offers"
    id = 123


class FakeClient:
    def __init__(self):
        self.connected = True
        self.handlers = []

    def is_connected(self):
        return self.connected

    def connect(self):
        self.connected = True

    def is_user_authorized(self):
        return True

    def disconnect(self):
        self.connected = False

    def get_entity(self, target):
        assert target == "amazinglootsdealsoffers"
        return FakeEntity()

    def iter_messages(self, entity, limit):
        return iter(
            [
                FakeMessage(12, "newer deal @ 5999"),
                FakeMessage(11, "older deal @ 4999"),
            ]
        )

    def add_event_handler(self, callback, event):
        self.handlers.append((callback, event))

    def remove_event_handler(self, callback, event):
        self.handlers.remove((callback, event))

    def run_until_disconnected(self):
        return None


def test_public_urls_normalize():
    assert (
        normalize_user_channel("https://t.me/amazinglootsdealsoffers")
        == "amazinglootsdealsoffers"
    )
    assert (
        normalize_user_channel("https://t.me/s/amazinglootsdealsoffers")
        == "amazinglootsdealsoffers"
    )


def test_invite_token_rejected():
    with pytest.raises(ValueError, match="Invite-link tokens"):
        normalize_user_channel("@+abc123")


def test_user_source_reads_external_public_channel():
    source = TelegramUserSource("12345", "hash", client=FakeClient())
    result = source.fetch_messages(
        "https://t.me/amazinglootsdealsoffers", limit=10
    )
    assert [m.message_id for m in result] == ["11", "12"]
    assert result[0].channel == "@amazinglootsdealsoffers"
    assert result[1].text == "newer deal @ 5999"


def test_user_source_cursor_prevents_repeat():
    source = TelegramUserSource("12345", "hash", client=FakeClient())
    assert len(source.fetch_messages("@amazinglootsdealsoffers")) == 2
    assert source.fetch_messages("@amazinglootsdealsoffers") == []


def test_user_source_requires_authorized_session():
    class Unauthorized(FakeClient):
        def is_user_authorized(self):
            return False

    with pytest.raises(TelegramUserReaderError, match="not authorized"):
        TelegramUserSource("12345", "hash", client=Unauthorized())


def test_message_from_event_preserves_channel_and_timestamp():
    class Event:
        chat_id = 123
        chat = FakeEntity()
        message = FakeMessage(44, "Samsung SSD @ 5999 https://example.com")

    message = TelegramUserSource.message_from_event(Event())
    assert isinstance(message, TelegramMessage)
    assert message.channel == "@amazinglootsdealsoffers"
    assert message.message_id == "44"
    assert message.text.startswith("Samsung SSD")
    assert message.observed_at == "2026-10-02T12:00:00+00:00"


def test_user_stream_registers_channel_event_handler():
    client = FakeClient()
    source = TelegramUserSource("12345", "hash", client=client)
    source.run_forever(
        ("https://t.me/amazinglootsdealsoffers",),
        lambda message: None,
    )
    assert len(client.handlers) == 0


def test_user_stream_skips_unresolvable_channel_and_keeps_good_channels():
    class PartiallyBrokenClient(FakeClient):
        def get_entity(self, target):
            if target == "broken":
                raise ValueError("not found")
            assert target == "amazinglootsdealsoffers"
            return FakeEntity()

    client = PartiallyBrokenClient()
    source = TelegramUserSource("12345", "hash", client=client)
    source.run_forever(
        ("@broken", "@amazinglootsdealsoffers"),
        lambda message: None,
    )
    assert len(client.handlers) == 0


def test_user_stream_fails_only_when_no_channels_can_be_resolved():
    class BrokenClient(FakeClient):
        def get_entity(self, target):
            raise ValueError("not found")

    source = TelegramUserSource("12345", "hash", client=BrokenClient())
    with pytest.raises(TelegramUserReaderError, match="any configured"):
        source.run_forever(("@broken-one", "@broken-two"), lambda message: None)
