import asyncio

from aiogram import Bot, Dispatcher

from yacloud_watcher.bot.router import create_router
from yacloud_watcher.config import Settings
from yacloud_watcher.scheduler.jobs import create_scheduler, setup_scheduler


async def main() -> None:
    settings = Settings()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    router = create_router(settings)
    dp.include_router(router)

    scheduler = create_scheduler()
    setup_scheduler(scheduler, bot, settings)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
