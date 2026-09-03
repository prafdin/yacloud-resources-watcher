"""Command handlers for the two things the bot answers directly.

``/start`` confirms the process is alive; ``/resources`` builds a snapshot on
demand and sends it, falling back to a one-line error if the collection itself
fails. The Yandex Cloud client is injected as dispatcher workflow data. A fresh
router is built per process via ``build_router`` so tests stay isolated.
"""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from yc_watcher.telegram.formatting import format_failure, format_snapshot, split_message
from yc_watcher.yc.client import YcClient
from yc_watcher.yc.inventory import collect_inventory

log = logging.getLogger(__name__)

LIVENESS = "Yandex Cloud Resources Watcher is running. Use /resources for a snapshot."
ROUTER_NAME = "commands"


async def handle_start(message: Message) -> None:
    await message.answer(LIVENESS)


async def handle_resources(message: Message, yc_client: YcClient) -> None:
    try:
        snapshot = await collect_inventory(yc_client)
    except Exception as error:
        log.exception("/resources failed to build the snapshot")
        await message.answer(format_failure(str(error)))
        return
    for chunk in split_message(format_snapshot(snapshot)):
        await message.answer(chunk)


def build_router() -> Router:
    router = Router(name=ROUTER_NAME)
    router.message.register(handle_start, CommandStart())
    router.message.register(handle_resources, Command("resources"))
    return router
