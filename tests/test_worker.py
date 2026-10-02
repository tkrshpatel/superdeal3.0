import pytest

from superdeal.database import connect, get_deal
from superdeal.telegram import MockTelegramSource, TelegramMessage
from superdeal.worker import WorkerConfig, run_once


def test_config_from_environment(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "@one, @two")
    config = WorkerConfig.from_env()
    assert config.token == "token"
    assert config.channels == ("@one", "@two")
    assert config.reader_mode == "bot"


def test_user_config_from_environment(monkeypatch):
    monkeypatch.setenv("TELEGRAM_READER_MODE", "user")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "https://t.me/deals")
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    config = WorkerConfig.from_env()
    assert config.reader_mode == "user"
    assert config.api_id == "12345"
    assert config.api_hash == "hash"


def test_config_validation():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        WorkerConfig("", ("@one",)).validate()
    with pytest.raises(ValueError, match="TELEGRAM_CHANNELS"):
        WorkerConfig("token", ()).validate()


def test_user_config_validation():
    with pytest.raises(ValueError, match="TELEGRAM_API_ID"):
        WorkerConfig("", ("@one",), reader_mode="user", api_hash="hash").validate()


def test_run_once_ingests_all_configured_channels():
    source = MockTelegramSource([
        TelegramMessage("@one", "1", "OnePlus Pad 2 @ 29699 https://amazon.in/p/1", "2026-09-29T20:00:00+00:00"),
        TelegramMessage("@two", "2", "Wonderchef Cooktop @ 3499 https://example.com/p/2", "2026-09-29T20:01:00+00:00"),
    ])
    config = WorkerConfig("token", ("@one", "@two"), database_url=":memory:")
    assert run_once(config, source=source) == 2


def test_worker_can_persist_to_sqlite(tmp_path):
    db = tmp_path / "superdeal.db"
    source = MockTelegramSource([
        TelegramMessage("@one", "1", "OnePlus Pad 2 @ 29699 https://amazon.in/p/1", "2026-09-29T20:00:00+00:00"),
    ])
    config = WorkerConfig("token", ("@one",), database_url=str(db))
    assert run_once(config, source=source) == 1
    connection = connect(str(db))
    try:
        assert get_deal(connection, 1)["current_price"] == 29699
    finally:
        connection.close()
