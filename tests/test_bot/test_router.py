from unittest.mock import Mock

from yacloud_watcher.bot.router import create_router


def test_create_router():
    settings = Mock()
    settings.telegram_allowed_user_ids = [123]
    router = create_router(settings)
    assert router is not None
