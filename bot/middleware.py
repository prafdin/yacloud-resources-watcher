"""Access control middleware."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class AccessControlMiddleware(BaseMiddleware):
    """Allow only the configured Telegram user to interact with the bot."""

    def __init__(self, allowed_user_id: int) -> None:
        super().__init__()
        self.allowed_user_id = allowed_user_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        if user_id != self.allowed_user_id:
            logger.warning("Unauthorized access attempt from user %s", user_id)
            if isinstance(event, Message):
                await event.answer("⛔ Access denied")
            return None
        return await handler(event, data)
