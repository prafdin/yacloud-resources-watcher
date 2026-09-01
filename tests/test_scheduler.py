"""Tests for scheduler jobs."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from storage.models import AllResources, ComputeInstance
from bot.scheduler import daily_report_job, reminder_check_job, setup_scheduler


async def test_daily_report_job(mock_config, mock_bot, database):
    """Test daily report job execution."""
    mock_bot.send_message.return_value = MagicMock(message_id=42, chat=MagicMock(id=123456789))
    snapshot = AllResources(
        compute_instances=[ComputeInstance(id="1", name="vm-1", status="RUNNING")]
    )
    with patch("bot.scheduler.fetch_all_resources", AsyncMock(return_value=snapshot)):
        await daily_report_job(mock_bot, mock_config, database)

    mock_bot.send_message.assert_called_once()
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "vm-1" in text
    assert await database.get_pending_count() == 1
    assert await database.get_total_reports_count() == 1


async def test_reminder_check_job(mock_config, mock_bot, database):
    """Test reminder check job."""
    sent_at = datetime.now(timezone.utc) - timedelta(hours=3)
    await database.save_pending_notification(
        message_id=10, chat_id=123456789, sent_at=sent_at
    )
    await reminder_check_job(mock_bot, mock_config, database)
    mock_bot.send_message.assert_called_once()
    pending = await database.get_unacknowledged_notifications()
    assert pending[0].reminder_sent is True


async def test_reminder_not_sent_before_timeout(mock_config, mock_bot, database):
    """Test reminder not sent before configured hours."""
    await database.save_pending_notification(
        message_id=10,
        chat_id=123456789,
        sent_at=datetime.now(timezone.utc),
    )
    await reminder_check_job(mock_bot, mock_config, database)
    mock_bot.send_message.assert_not_called()
    pending = await database.get_unacknowledged_notifications()
    assert pending[0].reminder_sent is False


async def test_reminder_not_sent_if_acknowledged(mock_config, mock_bot, database):
    """Test reminder not sent if already acknowledged."""
    sent_at = datetime.now(timezone.utc) - timedelta(hours=3)
    await database.save_pending_notification(
        message_id=10, chat_id=123456789, sent_at=sent_at
    )
    await database.acknowledge_notification(10, 123456789)
    await reminder_check_job(mock_bot, mock_config, database)
    mock_bot.send_message.assert_not_called()


async def test_reminder_not_sent_twice(mock_config, mock_bot, database):
    """Test reminder is sent only once."""
    sent_at = datetime.now(timezone.utc) - timedelta(hours=3)
    notification_id = await database.save_pending_notification(
        message_id=10, chat_id=123456789, sent_at=sent_at
    )
    await database.mark_reminder_sent(notification_id)
    await reminder_check_job(mock_bot, mock_config, database)
    mock_bot.send_message.assert_not_called()


def test_setup_scheduler(mock_config, mock_bot, database):
    """Test scheduler job registration."""
    scheduler = setup_scheduler(mock_bot, mock_config, database)
    assert scheduler.get_job("daily_report") is not None
    assert scheduler.get_job("reminder_check") is not None
