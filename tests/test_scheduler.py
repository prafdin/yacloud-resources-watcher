from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramAPIError
from apscheduler.triggers.cron import CronTrigger

from yc_watcher import scheduler as scheduler_module
from yc_watcher.models import DailyExpense, InventorySnapshot, Resource, ResourceGroup
from yc_watcher.scheduler import DAILY_JOB_ID, build_scheduler, send_daily_report

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


def _snapshot():
    return InventorySnapshot(
        "b1gfolder",
        NOW,
        (ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),)),),
        DailyExpense(amount=Decimal("12.34"), currency="RUB"),
    )


def _build(**overrides):
    kwargs = dict(
        bot=AsyncMock(), yc_client=object(), chat_id=555, hour=9, minute=30, timezone="UTC"
    )
    kwargs.update(overrides)
    return build_scheduler(**kwargs)


def test_scheduler_registers_a_single_daily_job():
    scheduler = _build()
    assert [job.id for job in scheduler.get_jobs()] == [DAILY_JOB_ID]


def test_daily_job_uses_a_cron_trigger_at_the_configured_time():
    job = _build().get_job(DAILY_JOB_ID)
    assert isinstance(job.trigger, CronTrigger)
    fields = {field.name: str(field) for field in job.trigger.fields}
    assert (fields["hour"], fields["minute"]) == ("9", "30")


async def test_send_daily_report_delivers_the_snapshot_to_the_chat(monkeypatch):
    monkeypatch.setattr(scheduler_module, "collect_inventory", AsyncMock(return_value=_snapshot()))
    bot = AsyncMock()
    await send_daily_report(
        bot, yc_client=object(), chat_id=555, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert bot.send_message.await_args_list[0].args[0] == 555
    assert "web-1" in bot.send_message.await_args_list[0].args[1]


async def test_send_daily_report_falls_back_to_an_error_message(monkeypatch):
    monkeypatch.setattr(
        scheduler_module, "collect_inventory", AsyncMock(side_effect=RuntimeError("bad key"))
    )
    bot = AsyncMock()
    await send_daily_report(
        bot, yc_client=object(), chat_id=555, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert bot.send_message.await_args.args[1] == (
        "⚠️ Could not build the inventory report: bad key"
    )


async def test_send_daily_report_survives_a_telegram_delivery_error(monkeypatch):
    monkeypatch.setattr(scheduler_module, "collect_inventory", AsyncMock(return_value=_snapshot()))
    bot = AsyncMock()
    bot.send_message.side_effect = TelegramAPIError(method=None, message="chat not found")
    await send_daily_report(
        bot, yc_client=object(), chat_id=555, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert bot.send_message.await_count == 1


async def test_send_daily_report_passes_billing_account_id_and_timezone(monkeypatch):
    monkeypatch.setattr(scheduler_module, "collect_inventory", AsyncMock(return_value=_snapshot()))
    bot = AsyncMock()
    await send_daily_report(
        bot, yc_client=object(), chat_id=555, billing_account_id="acc-1", tz=ZoneInfo("Europe/Amsterdam")
    )
    kwargs = scheduler_module.collect_inventory.await_args.kwargs
    assert (kwargs["billing_account_id"], kwargs["tz"]) == ("acc-1", ZoneInfo("Europe/Amsterdam"))


def test_daily_job_receives_the_billing_account_id_and_zone():
    job = _build(billing_account_id="acc-1", timezone="Europe/Amsterdam").get_job(DAILY_JOB_ID)
    assert (job.kwargs["billing_account_id"], job.kwargs["tz"]) == (
        "acc-1",
        ZoneInfo("Europe/Amsterdam"),
    )
