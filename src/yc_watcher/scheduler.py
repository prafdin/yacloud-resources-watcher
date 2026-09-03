"""Daily job that pushes the folder inventory to the configured chat.

Builds one cron-triggered ``AsyncIOScheduler`` job; the job itself never raises,
so a bad snapshot or a Telegram delivery hiccup is logged and the schedule keeps
running for the next day.
"""

import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from yc_watcher.telegram.formatting import format_failure, format_snapshot, split_message
from yc_watcher.yc.client import YcClient
from yc_watcher.yc.inventory import collect_inventory

log = logging.getLogger(__name__)
DAILY_JOB_ID = "daily-inventory"


async def send_daily_report(bot: Bot, yc_client: YcClient, chat_id: int) -> None:
    try:
        chunks = split_message(format_snapshot(await collect_inventory(yc_client)))
    except Exception as error:
        log.exception("scheduled inventory build failed")
        chunks = [format_failure(str(error))]
    for chunk in chunks:
        try:
            await bot.send_message(chat_id, chunk)
        except TelegramAPIError:
            log.exception("failed to deliver scheduled report to chat_id=%s", chat_id)


def build_scheduler(
    bot: Bot,
    yc_client: YcClient,
    *,
    chat_id: int,
    hour: int,
    minute: int,
    timezone: str,
) -> AsyncIOScheduler:
    zone = ZoneInfo(timezone)
    scheduler = AsyncIOScheduler(timezone=zone)
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=hour, minute=minute, timezone=zone),
        kwargs={"bot": bot, "yc_client": yc_client, "chat_id": chat_id},
        id=DAILY_JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    return scheduler
