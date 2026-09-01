"""Bot entry point."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher

from bot.handlers import router
from bot.middleware import AccessControlMiddleware
from bot.scheduler import setup_scheduler
from config.settings import Config, load_config
from storage.database import Database

logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.format,
    )


async def main() -> None:
    """Initialize and start the bot."""
    config = load_config()
    setup_logging(config)
    logger.info("Starting Yandex Cloud Resources Watcher Bot")

    db = Database(config.storage.database_path)
    await db.init()

    bot = Bot(token=config.telegram.bot_token)
    dp = Dispatcher()
    dp.message.outer_middleware(
        AccessControlMiddleware(config.telegram.allowed_user_id)
    )
    dp.include_router(router)

    scheduler = setup_scheduler(bot, config, db)
    start_time = datetime.now(timezone.utc)
    dp.workflow_data.update(
        {
            "config": config,
            "db": db,
            "scheduler": scheduler,
            "start_time": start_time,
        }
    )

    scheduler.start()
    logger.info(
        "Scheduler started, daily report at %s (%s)",
        config.scheduler.daily_report_time,
        config.scheduler.timezone,
    )

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
