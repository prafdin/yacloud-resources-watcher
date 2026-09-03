from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from yc_watcher.telegram.access import WhitelistMiddleware


def _message():
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    return message


@pytest.fixture
def handler():
    return AsyncMock(return_value="handled")


async def test_allowed_user_reaches_the_handler(handler):
    middleware = WhitelistMiddleware(frozenset({42}))
    message = _message()
    result = await middleware(handler, message, {"event_from_user": SimpleNamespace(id=42)})
    handler.assert_awaited_once_with(message, {"event_from_user": SimpleNamespace(id=42)})
    assert result == "handled"


async def test_disallowed_user_never_reaches_the_handler(handler):
    middleware = WhitelistMiddleware(frozenset({42}))
    await middleware(handler, _message(), {"event_from_user": SimpleNamespace(id=7)})
    handler.assert_not_awaited()


async def test_disallowed_user_gets_access_denied_reply(handler):
    middleware = WhitelistMiddleware(frozenset({42}))
    message = _message()
    await middleware(handler, message, {"event_from_user": SimpleNamespace(id=7)})
    message.answer.assert_awaited_once_with("Access denied.")


async def test_update_without_user_is_dropped(handler):
    middleware = WhitelistMiddleware(frozenset({42}))
    await middleware(handler, _message(), {})
    handler.assert_not_awaited()
