from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from yc_watcher import app as app_module
from yc_watcher.telegram.access import WhitelistMiddleware
from yc_watcher.telegram.handlers import ROUTER_NAME


def _settings():
    return SimpleNamespace(
        log_level="INFO",
        yc_sa_key_file="/secrets/sa-key.json",
        yc_folder_id="b1gfolder",
        telegram_bot_token=SimpleNamespace(get_secret_value=lambda: "123:abc"),
        allowed_user_ids=frozenset({42}),
        telegram_chat_id=555,
        schedule_hour=9,
        schedule_minute=30,
        schedule_timezone="UTC",
    )


def test_build_dispatcher_injects_the_client():
    client = object()
    dispatcher = app_module.build_dispatcher(_settings(), client)
    assert dispatcher["yc_client"] is client


def test_build_dispatcher_registers_the_command_router():
    dispatcher = app_module.build_dispatcher(_settings(), object())
    assert [r.name for r in dispatcher.sub_routers] == [ROUTER_NAME]


def test_build_dispatcher_registers_the_whitelist_middleware():
    dispatcher = app_module.build_dispatcher(_settings(), object())
    assert any(
        isinstance(mw, WhitelistMiddleware) for mw in dispatcher.message.outer_middleware
    )


@pytest.fixture
def patched(monkeypatch):
    scheduler = MagicMock()
    bot = MagicMock()
    bot.session.close = AsyncMock()
    monkeypatch.setattr(app_module, "configure_logging", MagicMock())
    monkeypatch.setattr(app_module.YcClient, "from_key_file", MagicMock(return_value=object()))
    monkeypatch.setattr(app_module, "Bot", MagicMock(return_value=bot))
    monkeypatch.setattr(app_module, "build_scheduler", MagicMock(return_value=scheduler))
    monkeypatch.setattr(app_module.Dispatcher, "start_polling", AsyncMock())
    return SimpleNamespace(scheduler=scheduler, bot=bot)


async def test_run_starts_then_shuts_down_the_scheduler(patched):
    await app_module.run(_settings())
    patched.scheduler.start.assert_called_once()
    patched.scheduler.shutdown.assert_called_once()


async def test_run_polls_the_bot(patched):
    await app_module.run(_settings())
    app_module.Dispatcher.start_polling.assert_awaited_once()


async def test_run_builds_the_client_from_the_configured_key(patched):
    settings = _settings()
    await app_module.run(settings)
    app_module.YcClient.from_key_file.assert_called_once_with(
        settings.yc_sa_key_file, settings.yc_folder_id
    )


async def test_run_closes_the_bot_session(patched):
    await app_module.run(_settings())
    patched.bot.session.close.assert_awaited_once()
