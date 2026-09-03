from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from yc_watcher.models import InventorySnapshot, Resource, ResourceGroup
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
        "b1gfolder", NOW, (ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),)),)
    )
    monkeypatch.setattr(handlers, "collect_inventory", AsyncMock(return_value=snapshot))
    await handlers.handle_resources(message, yc_client=object())
    assert "web-1" in message.answer.await_args_list[0].args[0]


async def test_resources_passes_the_injected_client(message, monkeypatch):
    collect = AsyncMock(
        return_value=InventorySnapshot("b1gfolder", NOW, (ResourceGroup("compute", "c", ()),))
    )
    monkeypatch.setattr(handlers, "collect_inventory", collect)
    client = object()
    await handlers.handle_resources(message, yc_client=client)
    assert collect.await_args.args[0] is client


async def test_resources_reports_failure_when_collection_raises(message, monkeypatch):
    monkeypatch.setattr(
        handlers, "collect_inventory", AsyncMock(side_effect=RuntimeError("token expired"))
    )
    await handlers.handle_resources(message, yc_client=object())
    assert message.answer.await_args.args[0] == (
        "⚠️ Could not build the inventory report: token expired"
    )


async def test_resources_splits_an_oversized_report_into_multiple_messages(message, monkeypatch):
    big = tuple(Resource(f"i{n}", f"instance-{n}") for n in range(2000))
    snapshot = InventorySnapshot(
        "b1gfolder", NOW, (ResourceGroup("compute", "🖥 Compute instances", big),)
    )
    monkeypatch.setattr(handlers, "collect_inventory", AsyncMock(return_value=snapshot))
    await handlers.handle_resources(message, yc_client=object())
    assert message.answer.await_count > 1
