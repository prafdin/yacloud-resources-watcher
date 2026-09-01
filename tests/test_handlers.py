"""Tests for bot handlers and access control."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message

from bot.handlers import (
    WELCOME_MESSAGE,
    cmd_help,
    cmd_resources,
    cmd_start,
    cmd_status,
    format_uptime,
    handle_text,
)
from bot.middleware import AccessControlMiddleware
from storage.models import AllResources, ComputeInstance


def _message(text: str = "/start", user_id: int = 123456789, chat_id: int = 123456789) -> AsyncMock:
    message = AsyncMock(spec=Message)
    message.text = text
    message.from_user = MagicMock(id=user_id)
    message.chat = MagicMock(id=chat_id)
    message.answer = AsyncMock()
    return message


async def test_start_command_authorized():
    """Test /start with authorized user."""
    message = _message("/start")
    await cmd_start(message)
    message.answer.assert_called_once_with(WELCOME_MESSAGE)


async def test_start_command_unauthorized():
    """Test /start with unauthorized user."""
    middleware = AccessControlMiddleware(allowed_user_id=123456789)
    handler = AsyncMock()
    event = _message("/start", user_id=999)
    await middleware(handler, event, {})
    event.answer.assert_called_once_with("⛔ Access denied")
    handler.assert_not_called()


async def test_resources_command(mock_config, database):
    """Test /resources command."""
    message = _message("/resources")
    snapshot = AllResources(
        compute_instances=[
            ComputeInstance(id="1", name="vm-1", status="RUNNING", cores=2, memory_gb=4)
        ]
    )
    with patch("bot.handlers.fetch_all_resources", AsyncMock(return_value=snapshot)):
        await cmd_resources(message, mock_config, database)
    message.answer.assert_called_once()
    text = message.answer.call_args[0][0]
    assert "vm-1" in text
    assert await database.get_total_reports_count() == 1
    assert await database.get_pending_count() == 0


async def test_resources_command_error(mock_config, database):
    """Test /resources when fetching fails."""
    message = _message("/resources")
    with patch(
        "bot.handlers.fetch_all_resources",
        AsyncMock(side_effect=RuntimeError("fail")),
    ):
        await cmd_resources(message, mock_config, database)
    message.answer.assert_called_once_with(
        "Failed to fetch resources. Please try again later."
    )


async def test_status_command(mock_config, database):
    """Test /status command."""
    message = _message("/status")
    scheduler = MagicMock()
    job = MagicMock()
    job.next_run_time = datetime(2024, 1, 15, 21, 0, 0)
    scheduler.get_job.return_value = job
    start_time = datetime(2024, 1, 10, 18, 0, 0, tzinfo=timezone.utc)
    await cmd_status(message, mock_config, database, scheduler, start_time)
    text = message.answer.call_args[0][0]
    assert "Bot is running" in text
    assert "2024-01-15 21:00:00" in text
    assert "Pending notifications: 0" in text
    assert "Total reports sent: 0" in text


async def test_help_command(mock_config):
    """Test /help command."""
    message = _message("/help")
    await cmd_help(message, mock_config)
    text = message.answer.call_args[0][0]
    assert "/resources" in text
    assert "21:00" in text
    assert "Europe/Moscow" in text


async def test_ok_acknowledgment(database):
    """Test OK text message handling."""
    await database.save_pending_notification(
        message_id=10,
        chat_id=123456789,
        sent_at=datetime.now(timezone.utc),
    )
    message = _message("ok")
    await handle_text(message, database)
    message.answer.assert_called_once_with("✅ Acknowledged")
    assert await database.get_pending_count() == 0


async def test_ok_without_pending(database):
    """Test OK when nothing is pending."""
    message = _message("OK")
    await handle_text(message, database)
    message.answer.assert_called_once_with("No pending reports to acknowledge.")


async def test_non_ok_text(database):
    """Test non-OK text replies."""
    message = _message("hello")
    await handle_text(message, database)
    message.answer.assert_called_once_with(
        "Please reply with OK to acknowledge the report"
    )


async def test_access_control_middleware():
    """Test access control middleware."""
    middleware = AccessControlMiddleware(allowed_user_id=123)
    handler = AsyncMock(return_value="ok")
    allowed = _message(user_id=123)
    denied = _message(user_id=456)

    result = await middleware(handler, allowed, {})
    assert result == "ok"
    handler.assert_called_once()

    handler.reset_mock()
    result = await middleware(handler, denied, {})
    assert result is None
    denied.answer.assert_called_once_with("⛔ Access denied")
    handler.assert_not_called()


def test_format_uptime():
    """Test uptime formatting."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    now = datetime(2024, 1, 6, 3, 0, tzinfo=timezone.utc)
    assert format_uptime(start, now) == "5 days, 3 hours"
