from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import grpc

import yc_watcher.yc.inventory as inventory_module
from yc_watcher.models import DailyExpense, Resource
from yc_watcher.yc.inventory import collect_inventory

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


def _client(folder_id="b1gfolder"):
    return type("FakeClient", (), {"folder_id": folder_id})()


class FakeSpec:
    def __init__(self, key, result=None, raises=None):
        self.key = key
        self.title = key.title()
        self._result = result or []
        self._raises = raises
        self.calls = 0

    def fetch(self, client):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._result


class FakeRpcError(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.PERMISSION_DENIED

    def details(self):
        return "denied"


class FakeBilling:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.calls = []

    def __call__(self, client, billing_account_id, day_start, day_end):
        self.calls.append((client, billing_account_id, day_start, day_end))
        if self._raises is not None:
            raise self._raises
        return self._result


async def test_successful_fetcher_populates_its_group():
    spec = FakeSpec("compute", result=[Resource("i1", "web-1")])
    snapshot = await collect_inventory(client=_client(), fetchers=(spec,), now=NOW)
    assert snapshot.groups[0].resources == (Resource("i1", "web-1"),)


async def test_failing_fetcher_becomes_a_failed_group_without_aborting_others():
    good = FakeSpec("compute", result=[Resource("i1", "web-1")])
    bad = FakeSpec("disks", raises=FakeRpcError())
    snapshot = await collect_inventory(client=_client(), fetchers=(good, bad), now=NOW)
    failed = {group.key: group for group in snapshot.groups}["disks"]
    assert failed.error == "PERMISSION_DENIED: denied"
    assert failed.resources == ()


async def test_good_group_survives_a_sibling_failure():
    good = FakeSpec("compute", result=[Resource("i1", "web-1")])
    bad = FakeSpec("disks", raises=FakeRpcError())
    snapshot = await collect_inventory(client=_client(), fetchers=(good, bad), now=NOW)
    assert {group.key: group for group in snapshot.groups}["compute"].count == 1


async def test_every_fetcher_runs_once():
    specs = [FakeSpec(f"type-{n}") for n in range(4)]
    await collect_inventory(client=_client(), fetchers=tuple(specs), now=NOW)
    assert [spec.calls for spec in specs] == [1, 1, 1, 1]


async def test_snapshot_uses_injected_timestamp_and_folder():
    client = type("C", (), {"folder_id": "b1gfolder"})()
    snapshot = await collect_inventory(client=client, fetchers=(FakeSpec("compute"),), now=NOW)
    assert (snapshot.folder_id, snapshot.generated_at) == ("b1gfolder", NOW)


async def test_group_order_follows_fetcher_order():
    specs = (FakeSpec("b"), FakeSpec("a"), FakeSpec("c"))
    snapshot = await collect_inventory(client=_client(), fetchers=specs, now=NOW)
    assert [group.key for group in snapshot.groups] == ["b", "a", "c"]


async def test_billing_success_populates_daily_expense(monkeypatch):
    expense = DailyExpense(amount=Decimal("12.34"), currency="RUB")
    monkeypatch.setattr(inventory_module, "fetch_daily_expense", FakeBilling(result=expense))
    snapshot = await collect_inventory(
        client=_client(), fetchers=(), now=NOW, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert snapshot.daily_expense == expense


async def test_billing_failure_becomes_an_error_without_aborting_resources(monkeypatch):
    monkeypatch.setattr(
        inventory_module, "fetch_daily_expense", FakeBilling(raises=RuntimeError("boom"))
    )
    good = FakeSpec("compute", result=[Resource("i1", "web-1")])
    snapshot = await collect_inventory(
        client=_client(), fetchers=(good,), now=NOW, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert snapshot.daily_expense.error == "RuntimeError: boom"
    assert snapshot.groups[0].resources == (Resource("i1", "web-1"),)


async def test_billing_receives_the_configured_account_id(monkeypatch):
    fake = FakeBilling(result=DailyExpense())
    monkeypatch.setattr(inventory_module, "fetch_daily_expense", fake)
    await collect_inventory(
        client=_client(), fetchers=(), now=NOW, billing_account_id="acc-1", tz=ZoneInfo("UTC")
    )
    assert fake.calls[0][1] == "acc-1"


async def test_billing_day_window_is_local_midnight_through_now(monkeypatch):
    fake = FakeBilling(result=DailyExpense())
    monkeypatch.setattr(inventory_module, "fetch_daily_expense", fake)
    now = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
    tz = ZoneInfo("Asia/Yekaterinburg")
    await collect_inventory(
        client=_client(), fetchers=(), now=now, billing_account_id="acc-1", tz=tz
    )
    _, _, day_start, day_end = fake.calls[0]
    assert (day_start, day_end) == (datetime(2026, 9, 3, 0, 0, tzinfo=tz), now.astimezone(tz))
