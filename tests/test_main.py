from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from yacloud_watcher.main import main


async def test_main():
    mock_settings = MagicMock()
    mock_settings.telegram_bot_token = "test-token"

    mock_bot = AsyncMock()
    mock_bot.session = AsyncMock()
    mock_bot.session.close = AsyncMock()

    mock_dp = MagicMock()
    mock_dp.start_polling = AsyncMock()

    mock_router = MagicMock()

    mock_scheduler = MagicMock()
    mock_scheduler.start = MagicMock()
    mock_scheduler.shutdown = MagicMock()

    with (
        patch("yacloud_watcher.main.Settings", return_value=mock_settings),
        patch("yacloud_watcher.main.Bot", return_value=mock_bot) as mock_bot_cls,
        patch("yacloud_watcher.main.Dispatcher", return_value=mock_dp) as mock_dp_cls,
        patch("yacloud_watcher.main.create_router", return_value=mock_router),
        patch("yacloud_watcher.main.create_scheduler", return_value=mock_scheduler),
        patch("yacloud_watcher.main.setup_scheduler") as mock_setup,
    ):
        await main()

    mock_bot_cls.assert_called_once_with(token="test-token")
    mock_dp_cls.assert_called_once()
    mock_dp.include_router.assert_called_once_with(mock_router)
    mock_setup.assert_called_once_with(mock_scheduler, mock_bot, mock_settings)
    mock_scheduler.start.assert_called_once()
    mock_dp.start_polling.assert_awaited_once_with(mock_bot)
    mock_scheduler.shutdown.assert_called_once()
    mock_bot.session.close.assert_awaited_once()


async def test_main_shutdown_on_error():
    mock_settings = MagicMock()
    mock_settings.telegram_bot_token = "test-token"

    mock_bot = AsyncMock()
    mock_bot.session = AsyncMock()
    mock_bot.session.close = AsyncMock()

    mock_dp = MagicMock()
    mock_dp.start_polling = AsyncMock(side_effect=RuntimeError("boom"))

    mock_scheduler = MagicMock()
    mock_scheduler.start = MagicMock()
    mock_scheduler.shutdown = MagicMock()

    with (
        patch("yacloud_watcher.main.Settings", return_value=mock_settings),
        patch("yacloud_watcher.main.Bot", return_value=mock_bot),
        patch("yacloud_watcher.main.Dispatcher", return_value=mock_dp),
        patch("yacloud_watcher.main.create_router", return_value=MagicMock()),
        patch("yacloud_watcher.main.create_scheduler", return_value=mock_scheduler),
        patch("yacloud_watcher.main.setup_scheduler"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await main()

    mock_scheduler.shutdown.assert_called_once()
    mock_bot.session.close.assert_awaited_once()
