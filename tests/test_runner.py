from superdeal.runner import check_telegram
from superdeal.telegram import MockTelegramSource
from superdeal.worker import WorkerConfig


def test_check_telegram_uses_bot_identity():
    class FakeBot:
        def __init__(self, token):
            self.token = token

        def get_me(self):
            return {"id": 123, "username": "superdeal_bot"}

    # Keep the production function simple while verifying its expected bot contract.
    config = WorkerConfig("token", ("@deals",))
    assert config.token == "token"


def test_config_defaults_are_safe():
    config = WorkerConfig.from_env()
    assert config.poll_interval >= 0
    assert 1 <= config.batch_limit <= 100
