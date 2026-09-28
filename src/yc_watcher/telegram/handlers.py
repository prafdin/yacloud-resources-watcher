"""Command handlers for the things the bot answers directly.

``/start`` confirms the process is alive; ``/help`` describes the schedule and
the commands; ``/resources`` builds a snapshot on demand and sends it, falling
back to a one-line error if the collection itself fails. ``COMMANDS`` is the
single list that both ``/help`` and the Telegram command menu are built from.
The Yandex Cloud client, the billing account id, the timezone and the schedule
are injected as dispatcher workflow data. A fresh
router is built per process via ``build_router`` so tests stay isolated.
"""

import logging
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from yc_watcher.telegram.formatting import format_failure, format_snapshot, split_message
from yc_watcher.yc.client import YcClient
from yc_watcher.yc.inventory import collect_inventory

log = logging.getLogger(__name__)

LIVENESS = "Yandex Cloud Resources Watcher is running. Use /help to see what it can do."
COMMANDS = (
    ("resources", "Build the report now"),
    ("help", "Show what the bot can do"),
    ("start", "Check the bot is alive"),
)
ROUTER_NAME = "commands"


async def handle_start(message: Message) -> None:
    await message.answer(LIVENESS)


async def handle_help(
    message: Message, schedule_time: str, schedule_timezone: str, folder_id: str
) -> None:
    await message.answer(
        "\n".join(
            (
                "Yandex Cloud Resources Watcher",
                f"Daily at {schedule_time} ({schedule_timezone}) posts the resources "
                f"in folder {folder_id} and yesterday's spend.",
                "",
                *(f"/{command} — {description}" for command, description in COMMANDS),
            )
        )
    )


async def handle_resources(
    message: Message, yc_client: YcClient, billing_account_id: str, tz: ZoneInfo
) -> None:
    try:
        snapshot = await collect_inventory(yc_client, billing_account_id=billing_account_id, tz=tz)
    except Exception as error:
        log.exception("/resources failed to build the snapshot")
        await message.answer(format_failure(str(error)))
        return
    for chunk in split_message(format_snapshot(snapshot)):
        await message.answer(chunk)


def build_router() -> Router:
    router = Router(name=ROUTER_NAME)
    router.message.register(handle_start, CommandStart())
    router.message.register(handle_help, Command("help"))
    router.message.register(handle_resources, Command("resources"))
    return router
