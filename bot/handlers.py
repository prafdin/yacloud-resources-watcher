"""Telegram command and message handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import Config
from storage.database import Database
from yandex_cloud.resources import fetch_all_resources, format_resources_message

logger = logging.getLogger(__name__)

router = Router()

WELCOME_MESSAGE = (
    "👋 Welcome to Yandex Cloud Resources Watcher!\n"
    "\n"
    "I'll send you daily reports about your cloud resources.\n"
    "\n"
    "Commands:\n"
    "/resources - Get current resource list\n"
    "/status - Check bot status\n"
    "/help - Show this help message"
)


def format_uptime(start_time: datetime, now: datetime | None = None) -> str:
    """Format process uptime as a human-readable string."""
    current = now or datetime.now(start_time.tzinfo or timezone.utc)
    if current.tzinfo != start_time.tzinfo:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(start_time.tzinfo)
    delta = current - start_time
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days > 0:
        return f"{days} days, {hours} hours"
    if hours > 0:
        return f"{hours} hours, {minutes} minutes"
    return f"{minutes} minutes"


def build_help_message(config: Config) -> str:
    """Build the help text using scheduler settings."""
    return (
        "📚 Available Commands\n"
        "\n"
        "/start - Welcome message and setup\n"
        "/resources - Get current resource list\n"
        "/status - Check bot and scheduler status\n"
        "/help - Show this help message\n"
        "\n"
        "📅 Daily Reports\n"
        f"I send resource reports every day at {config.scheduler.daily_report_time} "
        f"({config.scheduler.timezone}).\n"
        f'If you don\'t reply "OK" within {config.scheduler.reminder_hours} hours, '
        "I'll remind you.\n"
        "\n"
        "🔒 Access Control\n"
        "Only authorized users can interact with this bot."
    )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handle /start."""
    await message.answer(WELCOME_MESSAGE)


@router.message(Command("resources"))
async def cmd_resources(message: Message, config: Config, db: Database) -> None:
    """Handle /resources."""
    try:
        resources = await fetch_all_resources(config)
        text = format_resources_message(resources)
        await message.answer(text)
        await db.save_notification_history(
            sent_at=datetime.now(timezone.utc),
            resources_count=resources.total_count,
        )
    except Exception:
        logger.exception("Failed to handle /resources")
        await message.answer("Failed to fetch resources. Please try again later.")


@router.message(Command("status"))
async def cmd_status(
    message: Message,
    config: Config,
    db: Database,
    scheduler: AsyncIOScheduler,
    start_time: datetime,
) -> None:
    """Handle /status."""
    pending = await db.get_pending_count()
    total = await db.get_total_reports_count()
    job = scheduler.get_job("daily_report")
    if job and job.next_run_time:
        next_report = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        next_report = "not scheduled"
    text = (
        "🤖 Bot Status\n"
        "\n"
        "✅ Bot is running\n"
        f"📅 Next report: {next_report} ({config.scheduler.timezone})\n"
        f"📊 Pending notifications: {pending}\n"
        f"📜 Total reports sent: {total}\n"
        f"🕐 Uptime: {format_uptime(start_time)}"
    )
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message, config: Config) -> None:
    """Handle /help."""
    await message.answer(build_help_message(config))


@router.message(F.text)
async def handle_text(message: Message, db: Database) -> None:
    """Handle plain text, including OK acknowledgment."""
    text = (message.text or "").strip()
    if text.upper() == "OK":
        acknowledged = await db.acknowledge_latest_notification(message.chat.id)
        if acknowledged:
            await message.answer("✅ Acknowledged")
        else:
            await message.answer("No pending reports to acknowledge.")
        return
    await message.answer("Please reply with OK to acknowledge the report")
