"""APScheduler jobs for daily reports and reminders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import Config
from storage.database import Database
from yandex_cloud.resources import fetch_all_resources, format_resources_message

logger = logging.getLogger(__name__)

REMINDER_TEXT = (
    "⏰ Reminder: Please acknowledge the previous resource report by replying OK"
)


async def daily_report_job(bot: Bot, config: Config, db: Database) -> None:
    """Fetch resources, send a daily report, and track acknowledgment."""
    try:
        resources = await fetch_all_resources(config)
        message_text = format_resources_message(resources)
        sent_at = datetime.now(timezone.utc)
        message = await bot.send_message(
            chat_id=config.telegram.allowed_user_id,
            text=message_text,
        )
        await db.save_pending_notification(
            message_id=message.message_id,
            chat_id=message.chat.id,
            sent_at=sent_at,
        )
        await db.save_notification_history(
            sent_at=sent_at,
            resources_count=resources.total_count,
        )
        logger.info("Daily report sent, message_id=%s", message.message_id)
    except Exception:
        logger.exception("Daily report job failed")


async def reminder_check_job(bot: Bot, config: Config, db: Database) -> None:
    """Send reminders for unacknowledged reports after the configured delay."""
    try:
        pending = await db.get_unacknowledged_notifications()
        now = datetime.now(timezone.utc)
        threshold = timedelta(hours=config.scheduler.reminder_hours)
        for notification in pending:
            if notification.reminder_sent:
                continue
            if now - notification.sent_at < threshold:
                continue
            try:
                await bot.send_message(
                    chat_id=notification.chat_id,
                    text=REMINDER_TEXT,
                    reply_to_message_id=notification.message_id,
                )
            except Exception:
                logger.exception(
                    "Failed to send reminder for notification %s", notification.id
                )
                try:
                    await bot.send_message(
                        chat_id=notification.chat_id,
                        text=REMINDER_TEXT,
                    )
                except Exception:
                    logger.exception("Failed to send fallback reminder")
                    continue
            await db.mark_reminder_sent(notification.id)
            logger.info("Reminder sent for notification %s", notification.id)
    except Exception:
        logger.exception("Reminder check job failed")


def setup_scheduler(bot: Bot, config: Config, db: Database) -> AsyncIOScheduler:
    """Create and configure the async scheduler."""
    hour, minute = map(int, config.scheduler.daily_report_time.split(":"))
    scheduler = AsyncIOScheduler(timezone=config.scheduler.timezone)

    async def _daily_report() -> None:
        await daily_report_job(bot, config, db)

    async def _reminder_check() -> None:
        await reminder_check_job(bot, config, db)

    scheduler.add_job(
        _daily_report,
        CronTrigger(hour=hour, minute=minute, timezone=config.scheduler.timezone),
        id="daily_report",
        name="Daily Resource Report",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        _reminder_check,
        IntervalTrigger(minutes=30),
        id="reminder_check",
        name="Reminder Check",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler
