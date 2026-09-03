"""Message-level gate that lets only whitelisted Telegram users through.

Registered as an outer middleware on the dispatcher's message observer so a
stranger's update is logged and dropped before any command handler runs.
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

log = logging.getLogger(__name__)


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, allowed_user_ids: frozenset[int]) -> None:
        self._allowed = allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or user.id not in self._allowed:
            log.warning("blocked update from user_id=%s", getattr(user, "id", None))
            if isinstance(event, Message):
                await event.answer("Access denied.")
            return None
        return await handler(event, data)
