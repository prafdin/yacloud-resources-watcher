from aiogram import Router

from yacloud_watcher.bot.handlers import register_handlers
from yacloud_watcher.config import Settings


def create_router(settings: Settings) -> Router:
    router = Router()
    register_handlers(router, settings)
    return router
