from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from yacloud_watcher.cloud.client import YCClient
from yacloud_watcher.cloud.resources import get_all_resources
from yacloud_watcher.config import Settings


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    return scheduler


async def send_scheduled_notification(bot: Bot, settings: Settings) -> None:
    try:
        client = YCClient(
            service_account_key_file=settings.yc_service_account_key_file,
            folder_id=settings.yc_folder_id
        )
        resources = get_all_resources(client)

        if not resources:
            message = "Ресурсы не найдены."
        else:
            grouped: dict[str, list] = {}
            for resource in resources:
                grouped.setdefault(resource.resource_type, []).append(resource)

            message = ""
            for resource_type, items in grouped.items():
                emoji = "🖥" if resource_type == "compute" else "📦"
                message += f"{emoji} {resource_type.title()} ({len(items)}):\n"
                for item in items:
                    message += item.format() + "\n"
                message += "\n"
            message = message.strip()

        for user_id in settings.telegram_allowed_user_ids:
            await bot.send_message(user_id, message)
    except Exception as e:
        print(f"Error sending scheduled notification: {e}")


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot, settings: Settings) -> None:
    hours, minutes = settings.schedule_time.split(":")

    trigger = CronTrigger(
        hour=int(hours),
        minute=int(minutes),
        timezone=settings.schedule_timezone
    )

    scheduler.add_job(
        send_scheduled_notification,
        trigger=trigger,
        args=[bot, settings],
        id="daily_notification"
    )
