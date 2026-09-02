import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from yacloud_watcher.bot.router import create_router
from yacloud_watcher.config import Settings
from yacloud_watcher.scheduler.jobs import create_scheduler, setup_scheduler


async def main() -> None:
    settings = Settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)
    logger.info("Bot starting with log level: %s", settings.log_level)

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    router = create_router(settings)
    dp.include_router(router)

    scheduler = create_scheduler()
    setup_scheduler(scheduler, bot, settings)
    scheduler.start()

    logger.info("Bot polling started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
