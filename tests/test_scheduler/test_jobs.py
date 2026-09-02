from unittest.mock import AsyncMock, Mock, patch

import pytest
from yacloud_watcher.scheduler.jobs import create_scheduler, send_scheduled_notification


def test_create_scheduler():
    scheduler = create_scheduler()
    assert scheduler is not None


def _make_settings():
    settings = Mock()
    settings.telegram_allowed_user_ids = [123456]
    settings.yc_service_account_key_file = "/fake/key.json"
    settings.yc_folder_id = "fake-folder"
    return settings


@pytest.mark.asyncio
async def test_send_scheduled_notification_error_logs():
    bot = Mock()
    bot.send_message = AsyncMock()
    settings = _make_settings()

    with (
        patch("yacloud_watcher.scheduler.jobs.YCClient"),
        patch(
            "yacloud_watcher.scheduler.jobs.get_all_resources",
            side_effect=RuntimeError("connection failed"),
        ),
        patch("yacloud_watcher.scheduler.jobs.logger") as mock_logger,
    ):
        await send_scheduled_notification(bot, settings)

    mock_logger.exception.assert_called_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_scheduled_notification_success_logs():
    bot = Mock()
    bot.send_message = AsyncMock()
    settings = _make_settings()

    with (
        patch("yacloud_watcher.scheduler.jobs.YCClient"),
        patch(
            "yacloud_watcher.scheduler.jobs.get_all_resources",
            return_value=[],
        ),
        patch("yacloud_watcher.scheduler.jobs.logger") as mock_logger,
    ):
        await send_scheduled_notification(bot, settings)

    mock_logger.info.assert_called_once()
    bot.send_message.assert_awaited_once()
