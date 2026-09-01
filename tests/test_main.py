"""Tests for bot entry point."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.main import main, setup_logging
from config.settings import Config


async def test_main_starts_and_stops(mock_config: Config, temp_db_path: str) -> None:
    """Test bot startup wires middleware, scheduler and polling."""
    mock_config.storage.database_path = temp_db_path
    bot = AsyncMock()
    dispatcher = MagicMock()
    dispatcher.start_polling = AsyncMock()
    dispatcher.workflow_data = {}
    dispatcher.message = MagicMock()
    scheduler = MagicMock()

    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.Bot", return_value=bot),
        patch("bot.main.Dispatcher", return_value=dispatcher),
        patch("bot.main.setup_scheduler", return_value=scheduler),
    ):
        await main()

    dispatcher.include_router.assert_called()
    dispatcher.message.outer_middleware.assert_called()
    dispatcher.start_polling.assert_awaited_once_with(bot)
    scheduler.start.assert_called_once()
    scheduler.shutdown.assert_called_once()
    bot.session.close.assert_awaited()


def test_setup_logging(mock_config: Config) -> None:
    """Test logging configuration."""
    setup_logging(mock_config)
