"""Process wiring and lifecycle.

Builds the Yandex Cloud client, the aiogram dispatcher (whitelist + commands)
and the daily scheduler, then runs long-polling until interrupted and tears the
scheduler and bot session down on the way out.
"""

import asyncio

from aiogram import Bot, Dispatcher

from yc_watcher.config import Settings, load_settings
from yc_watcher.logging_setup import configure_logging
from yc_watcher.scheduler import build_scheduler
from yc_watcher.telegram.access import WhitelistMiddleware
from yc_watcher.telegram.handlers import build_router
from yc_watcher.yc.client import YcClient


def build_dispatcher(settings: Settings, yc_client: YcClient) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["yc_client"] = yc_client
    dispatcher["billing_account_id"] = settings.yc_billing_account_id
    dispatcher["tz"] = settings.tzinfo
    dispatcher.message.outer_middleware(WhitelistMiddleware(settings.allowed_user_ids))
    dispatcher.include_router(build_router())
    return dispatcher


async def run(settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    yc_client = YcClient.from_key_file(settings.yc_sa_key_file, settings.yc_folder_id)
    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    dispatcher = build_dispatcher(settings, yc_client)
    scheduler = build_scheduler(
        bot,
        yc_client,
        chat_id=settings.telegram_chat_id,
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.schedule_timezone,
        billing_account_id=settings.yc_billing_account_id,
    )

    scheduler.start()
    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


def main() -> None:
    asyncio.run(run())
