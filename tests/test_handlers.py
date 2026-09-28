from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from yc_watcher.models import DailyExpense, InventorySnapshot, Resource, ResourceGroup
from yc_watcher.telegram import handlers

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def message():
    stub = AsyncMock()
    stub.answer = AsyncMock()
    return stub


async def test_start_replies_with_a_liveness_line(message):
    await handlers.handle_start(message)
    message.answer.assert_awaited_once()
    assert "running" in message.answer.await_args.args[0].lower()


async def test_resources_sends_the_formatted_snapshot(message, monkeypatch):
    snapshot = InventorySnapshot(
        "b1gfolder", NOW, (ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),)),), DailyExpense(amount=Decimal("0"), currency="RUB")
    )
    monkeypatch.setattr(handlers, "collect_inventory", AsyncMock(return_value=snapshot))
    await handlers.handle_resources(
        message, yc_client=object(), billing_account_id="acc-1"
    )
    assert "web-1" in message.answer.await_args_list[0].args[0]


async def test_resources_passes_the_injected_client(message, monkeypatch):
    collect = AsyncMock(
        return_value=InventorySnapshot("b1gfolder", NOW, (ResourceGroup("compute", "c", ()),), DailyExpense(amount=Decimal("0"), currency="RUB"))
    )
    monkeypatch.setattr(handlers, "collect_inventory", collect)
    client = object()
    await handlers.handle_resources(
        message, yc_client=client, billing_account_id="acc-1"
    )
    assert collect.await_args.args[0] is client


async def test_resources_passes_only_the_billing_account_id(message, monkeypatch):
    collect = AsyncMock(
        return_value=InventorySnapshot(
            "b1gfolder", NOW, (), DailyExpense(amount=Decimal("0"), currency="RUB")
        )
    )
    monkeypatch.setattr(handlers, "collect_inventory", collect)
    await handlers.handle_resources(
        message, yc_client=object(), billing_account_id="acc-7q"
    )
    kwargs = collect.await_args.kwargs
    assert kwargs == {"billing_account_id": "acc-7q"}, "resources passes more than the account"


async def test_resources_reports_failure_when_collection_raises(message, monkeypatch):
    monkeypatch.setattr(
        handlers, "collect_inventory", AsyncMock(side_effect=RuntimeError("token expired"))
    )
    await handlers.handle_resources(
        message, yc_client=object(), billing_account_id="acc-1"
    )
    assert message.answer.await_args.args[0] == (
        "⚠️ Could not build the inventory report: token expired"
    )


async def test_resources_splits_an_oversized_report_into_multiple_messages(message, monkeypatch):
    big = tuple(Resource(f"i{n}", f"instance-{n}") for n in range(2000))
    snapshot = InventorySnapshot(
        "b1gfolder", NOW, (ResourceGroup("compute", "🖥 Compute instances", big),), DailyExpense(amount=Decimal("0"), currency="RUB")
    )
    monkeypatch.setattr(handlers, "collect_inventory", AsyncMock(return_value=snapshot))
    await handlers.handle_resources(
        message, yc_client=object(), billing_account_id="acc-1"
    )
    assert message.answer.await_count > 1


async def test_help_lists_the_resources_command(message):
    await handlers.handle_help(
        message, schedule_time="07:45", schedule_timezone="Asia/Tokyo", folder_id="b1gzx9"
    )
    assert "/resources" in message.answer.await_args.args[0], "help does not list /resources"


async def test_help_shows_the_configured_schedule(message):
    await handlers.handle_help(
        message, schedule_time="07:45", schedule_timezone="Asia/Tokyo", folder_id="b1gzx9"
    )
    assert "07:45 (Asia/Tokyo)" in message.answer.await_args.args[0], "help hides the schedule"


async def test_help_shows_the_watched_folder(message):
    await handlers.handle_help(
        message, schedule_time="07:45", schedule_timezone="Asia/Tokyo", folder_id="b1gzx9"
    )
    assert "b1gzx9" in message.answer.await_args.args[0], "help hides the folder"


async def test_start_points_to_help(message):
    await handlers.handle_start(message)
    assert "/help" in message.answer.await_args.args[0], "start does not mention /help"


def test_router_answers_the_help_command():
    router = handlers.build_router()
    commands = {
        command
        for handler in router.message.handlers
        for flt in handler.filters
        for command in getattr(flt.callback, "commands", ())
    }
    assert "help" in commands, "router does not answer /help"
