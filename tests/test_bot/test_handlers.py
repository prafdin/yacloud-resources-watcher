from unittest.mock import AsyncMock, Mock, patch

import pytest
from yacloud_watcher.bot.handlers import register_handlers
from yacloud_watcher.cloud.models import Resource


def _make_settings(allowed_ids=None):
    settings = Mock()
    settings.telegram_allowed_user_ids = allowed_ids or [123456]
    settings.yc_service_account_key_file = "/fake/key.json"
    settings.yc_folder_id = "fake-folder"
    return settings


def _make_message(user_id=123456):
    message = Mock()
    message.from_user = Mock()
    message.from_user.id = user_id
    message.answer = AsyncMock()
    return message


def _get_handler(router, index):
    return router.message.return_value.call_args_list[index].args[0]


def test_register_handlers_attaches_three():
    router = Mock()
    settings = _make_settings()
    register_handlers(router, settings)
    assert router.message.return_value.call_count == 3


@pytest.mark.asyncio
async def test_start_handler_sends_welcome():
    router = Mock()
    settings = _make_settings(allowed_ids=[123456])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 0)
    message = _make_message(user_id=123456)
    await handler_fn(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "Привет" in text
    assert "/resources" in text
    assert "/help" in text


@pytest.mark.asyncio
async def test_start_handler_rejects_unauthorized():
    router = Mock()
    settings = _make_settings(allowed_ids=[999999])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 0)
    message = _make_message(user_id=123456)
    await handler_fn(message)

    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_resources_handler_no_resources():
    router = Mock()
    settings = _make_settings(allowed_ids=[123456])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 1)
    message = _make_message(user_id=123456)

    with patch("yacloud_watcher.bot.handlers.YCClient"), patch(
        "yacloud_watcher.bot.handlers.get_all_resources", return_value=[]
    ):
        await handler_fn(message)

    message.answer.assert_awaited_once_with("Ресурсы не найдены.")


@pytest.mark.asyncio
async def test_resources_handler_with_resources():
    router = Mock()
    settings = _make_settings(allowed_ids=[123456])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 1)
    message = _make_message(user_id=123456)

    resources = [
        Resource(
            name="vm-1",
            resource_type="compute",
            status="RUNNING",
            zone="ru-central1-a",
        ),
        Resource(
            name="vm-2",
            resource_type="compute",
            status="STOPPED",
            zone="ru-central1-b",
        ),
    ]

    with (
        patch("yacloud_watcher.bot.handlers.YCClient"),
        patch(
            "yacloud_watcher.bot.handlers.get_all_resources",
            return_value=resources,
        ),
    ):
        await handler_fn(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "Compute" in text
    assert "vm-1" in text
    assert "vm-2" in text
    assert "(2)" in text


@pytest.mark.asyncio
async def test_resources_handler_rejects_unauthorized():
    router = Mock()
    settings = _make_settings(allowed_ids=[999999])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 1)
    message = _make_message(user_id=123456)
    await handler_fn(message)

    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_resources_handler_error():
    router = Mock()
    settings = _make_settings(allowed_ids=[123456])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 1)
    message = _make_message(user_id=123456)

    with (
        patch("yacloud_watcher.bot.handlers.YCClient"),
        patch(
            "yacloud_watcher.bot.handlers.get_all_resources",
            side_effect=RuntimeError("connection failed"),
        ),
        patch("yacloud_watcher.bot.handlers.logger") as mock_logger,
    ):
        await handler_fn(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "Не удалось получить ресурсы" in text
    assert "connection failed" not in text
    mock_logger.exception.assert_called_once()


@pytest.mark.asyncio
async def test_help_handler_sends_help():
    router = Mock()
    settings = _make_settings(allowed_ids=[123456])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 2)
    message = _make_message(user_id=123456)
    await handler_fn(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "/start" in text
    assert "/resources" in text
    assert "/help" in text


@pytest.mark.asyncio
async def test_help_handler_rejects_unauthorized():
    router = Mock()
    settings = _make_settings(allowed_ids=[999999])
    register_handlers(router, settings)

    handler_fn = _get_handler(router, 2)
    message = _make_message(user_id=123456)
    await handler_fn(message)

    message.answer.assert_not_awaited()
