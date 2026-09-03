# Daily Expense In Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show how much has been spent on the folder's billing account so far today, as a new line in the Telegram inventory report's header.

**Architecture:** A new `yc/billing.py` module wraps `ConsumptionCoreService.GetFolderUsageReport` the same way `yc/fetchers.py` wraps the resource-listing RPCs — one small function, `client.stub(...)`, one request, one response, no retries. `collect_inventory` runs it inside the same `asyncio.gather` as the resource fetchers, catching its errors exactly like a `FetcherSpec` failure, so a billing outage never blocks the resource report. The result rides on `InventorySnapshot.daily_expense` and gets one new line in `format_snapshot`.

**Tech Stack:** Python 3.12, `yandexcloud` SDK (`yandex.cloud.billing.usage_records.v1`), `pydantic-settings`, `pytest` + `pytest-asyncio`.

**Spec:** `docs/superpowers/specs/2026-09-03-daily-expense-in-report-design.md`

## Global Constraints

- `expense` (net of discounts/credits), not `cost`, is the number shown — per spec.
- The day window is local midnight (`schedule_timezone`) through the moment of report generation — per spec.
- `YC_BILLING_ACCOUNT_ID` is a **required** `Settings` field, no default — per spec.
- A billing fetch failure must not abort the resource report — it becomes an inline `⚠️ fetch failed: ...` note, same isolation `FetcherSpec` failures already get.
- The existing `INCOMPLETE_NOTE` trailer ("counts above may be incomplete") is untouched — it is about resource counts, not money.
- `collect_inventory`'s new `billing_account_id`/`tz` parameters, and `send_daily_report`/`build_scheduler`'s new `billing_account_id` parameter, all get defaults (`""` / `ZoneInfo("UTC")`) so every pre-existing test in `test_inventory.py` and `test_scheduler.py` keeps passing unmodified — only tests that exercise billing behavior touch these parameters explicitly.

---

### Task 1: `DailyExpense` model and `InventorySnapshot.daily_expense`

**Files:**
- Modify: `src/yc_watcher/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `DailyExpense(amount: Decimal | None = None, currency: str | None = None, error: str | None = None)` with property `failed -> bool`.
- Produces: `InventorySnapshot(folder_id, generated_at, groups, daily_expense: DailyExpense)` — `daily_expense` is now a required 4th positional field.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_models.py` (needs `from decimal import Decimal` and `DailyExpense` added to the existing `from yc_watcher.models import ...` line):

```python
def test_daily_expense_without_error_is_not_failed():
    assert DailyExpense(amount=Decimal("1.00"), currency="RUB").failed is False


def test_daily_expense_with_error_is_failed():
    assert DailyExpense(error="PERMISSION_DENIED").failed is True


def test_daily_expense_defaults_to_no_amount_currency_or_error():
    expense = DailyExpense()
    assert (expense.amount, expense.currency, expense.error) == (None, None, None)
```

And update every existing direct `InventorySnapshot(...)` call in this file to pass a 4th positional argument, `DailyExpense()` — there are four: `test_snapshot_total_sums_group_counts`, `test_snapshot_any_failed_is_true_when_a_group_failed`, `test_snapshot_is_empty_when_no_resources_and_no_failures`, `test_snapshot_is_not_empty_when_a_group_failed`. Example:

```python
def test_snapshot_total_sums_group_counts():
    snapshot = InventorySnapshot(
        "b1g",
        NOW,
        (_group("a", [Resource("1", "1")]), _group("b", [Resource("2", "2"), Resource("3", "3")])),
        DailyExpense(),
    )
    assert snapshot.total == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: the 3 new tests FAIL with `ImportError`/`NameError` (`DailyExpense` doesn't exist yet), and the 4 updated `InventorySnapshot(...)` call sites FAIL with `TypeError: __init__() takes ... positional arguments` until the model changes.

- [ ] **Step 3: Implement the model**

In `src/yc_watcher/models.py`, add the import and the new dataclass, and extend `InventorySnapshot`:

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
```

```python
@dataclass(frozen=True, slots=True)
class DailyExpense:
    amount: Decimal | None = None
    currency: str | None = None
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None
```

```python
@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    folder_id: str
    generated_at: datetime
    groups: tuple[ResourceGroup, ...]
    daily_expense: DailyExpense

    @property
    def total(self) -> int:
        return sum(group.count for group in self.groups)

    @property
    def any_failed(self) -> bool:
        return any(group.failed for group in self.groups)

    @property
    def is_empty(self) -> bool:
        return self.total == 0 and not self.any_failed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/models.py tests/test_models.py
git commit -m "Add DailyExpense and wire it into InventorySnapshot"
```

---

### Task 2: `YC_BILLING_ACCOUNT_ID` configuration

**Files:**
- Modify: `src/yc_watcher/config.py`
- Modify: `.env.example`
- Modify: `README.md`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings.yc_billing_account_id: str` (required, no default).

- [ ] **Step 1: Write the failing tests**

Add `"YC_BILLING_ACCOUNT_ID": "foo123"` to `BASE_ENV` in `tests/test_config.py`:

```python
BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "123:abc",
    "TELEGRAM_ALLOWED_USER_IDS": "111, 222 ,333",
    "TELEGRAM_CHAT_ID": "111",
    "YC_SA_KEY_FILE": "/secrets/sa-key.json",
    "YC_FOLDER_ID": "b1gfolder",
    "YC_BILLING_ACCOUNT_ID": "foo123",
    "SCHEDULE_TIME": "09:30",
    "SCHEDULE_TIMEZONE": "Europe/Amsterdam",
    "LOG_LEVEL": "INFO",
}
```

Add a new test:

```python
def test_missing_billing_account_id_is_rejected():
    env = {k: v for k, v in BASE_ENV.items() if k != "YC_BILLING_ACCOUNT_ID"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{k.lower(): v for k, v in env.items()})
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `pytest tests/test_config.py -v`
Expected: `test_missing_billing_account_id_is_rejected` FAILS — `Settings` currently accepts the env without `YC_BILLING_ACCOUNT_ID` (extra="ignore" means the other tests still pass at this point).

- [ ] **Step 3: Add the field**

In `src/yc_watcher/config.py`, add alongside `yc_folder_id`:

```python
    yc_folder_id: str
    yc_billing_account_id: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Document the new variable**

In `.env.example`, under the `# Yandex Cloud` section:

```
YC_SA_KEY_FILE=./sa-key.json
YC_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx
YC_BILLING_ACCOUNT_ID=dn2xxxxxxxxxxxxxxxxx
```

In `README.md`'s configuration table, add a row right after `YC_FOLDER_ID`:

```
| `YC_BILLING_ACCOUNT_ID` | Billing account to read today's spend from |
```

and update the permissions line right below the table:

```
The service account needs `viewer` on the folder (or per-service viewer roles) and `billing.accounts.viewer` on the billing account.
```

- [ ] **Step 6: Commit**

```bash
git add src/yc_watcher/config.py tests/test_config.py .env.example README.md
git commit -m "Add required YC_BILLING_ACCOUNT_ID setting"
```

---

### Task 3: `yc/billing.py` — fetch today's spend from Yandex Cloud

**Files:**
- Create: `src/yc_watcher/yc/billing.py`
- Test: `tests/test_billing.py`

**Interfaces:**
- Consumes: `DailyExpense` from Task 1 (`yc_watcher.models`).
- Produces: `fetch_daily_expense(client, billing_account_id: str, day_start: datetime, day_end: datetime) -> DailyExpense`. Raises on failure — does **not** catch (the caller, Task 4, does).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_billing.py`:

```python
"""Fetches how much has been spent on the folder's billing account for a date window."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from yandex.cloud.billing.usage_records.v1.consumption_core_service_pb2 import (
    FolderUsageReportResponse,
)

from yc_watcher.models import DailyExpense
from yc_watcher.yc.billing import fetch_daily_expense

DAY_START = datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc)
DAY_END = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
RUB = 1  # Currency.RUB


def _response(expense="123.45", currency=RUB):
    response = FolderUsageReportResponse(currency=currency)
    response.expense.value = expense
    return response


class FakeStub:
    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.requests = []

    def GetFolderUsageReport(self, request):
        self.requests.append(request)
        if self._raises is not None:
            raise self._raises
        return self._response


class FakeClient:
    def __init__(self, stub, folder_id="b1gfolder"):
        self.folder_id = folder_id
        self._stub = stub

    def stub(self, stub_ctor):
        return self._stub


def test_returns_expense_amount_and_currency():
    client = FakeClient(FakeStub(_response(expense="123.45", currency=RUB)))
    result = fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
    assert result == DailyExpense(amount=Decimal("123.45"), currency="RUB")


def test_sends_billing_account_id_and_folder_id_in_the_request():
    stub = FakeStub(_response())
    client = FakeClient(stub, folder_id="b1gfolder")
    fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
    request = stub.requests[0]
    assert (request.billing_account_id, list(request.folder_ids)) == ("acc-1", ["b1gfolder"])


def test_sends_the_day_window_as_the_request_timestamps():
    stub = FakeStub(_response())
    client = FakeClient(stub)
    fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
    request = stub.requests[0]
    assert (
        request.start_date.ToDatetime(tzinfo=timezone.utc),
        request.end_date.ToDatetime(tzinfo=timezone.utc),
    ) == (DAY_START, DAY_END)


def test_propagates_errors_from_the_stub_without_catching_them():
    client = FakeClient(FakeStub(raises=RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_billing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'yc_watcher.yc.billing'`

- [ ] **Step 3: Implement `fetch_daily_expense`**

Create `src/yc_watcher/yc/billing.py`:

```python
"""Fetches how much has been spent on the folder's billing account today.

Mirrors ``FetcherSpec.fetch`` from ``yc/fetchers.py``: one stub, one request,
one response. This raises on failure and leaves catching it to the caller,
the same division of labor ``collect_inventory`` already has with fetchers.
"""

from datetime import datetime
from decimal import Decimal

from google.protobuf.timestamp_pb2 import Timestamp
from yandex.cloud.billing.usage_records.v1.common_types_pb2 import Currency
from yandex.cloud.billing.usage_records.v1.consumption_core_service_pb2 import (
    UsageReportRequest,
)
from yandex.cloud.billing.usage_records.v1.consumption_core_service_pb2_grpc import (
    ConsumptionCoreServiceStub,
)

from yc_watcher.models import DailyExpense


def fetch_daily_expense(
    client, billing_account_id: str, day_start: datetime, day_end: datetime
) -> DailyExpense:
    stub = client.stub(ConsumptionCoreServiceStub)
    start_ts, end_ts = Timestamp(), Timestamp()
    start_ts.FromDatetime(day_start)
    end_ts.FromDatetime(day_end)
    request = UsageReportRequest(
        billing_account_id=billing_account_id,
        start_date=start_ts,
        end_date=end_ts,
        folder_ids=[client.folder_id],
    )
    response = stub.GetFolderUsageReport(request)
    return DailyExpense(
        amount=Decimal(response.expense.value), currency=Currency.Name(response.currency)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_billing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/yc/billing.py tests/test_billing.py
git commit -m "Add fetch_daily_expense for the folder's billing account"
```

---

### Task 4: Wire billing into `collect_inventory`

**Files:**
- Modify: `src/yc_watcher/yc/inventory.py`
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: `fetch_daily_expense` from Task 3, `DailyExpense` from Task 1.
- Produces: `collect_inventory(client, fetchers=FETCHERS, now=None, billing_account_id: str = "", tz: ZoneInfo = ZoneInfo("UTC")) -> InventorySnapshot` — `InventorySnapshot.daily_expense` is now populated.

- [ ] **Step 1: Write the failing tests**

Update the imports at the top of `tests/test_inventory.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import grpc

import yc_watcher.yc.inventory as inventory_module
from yc_watcher.models import DailyExpense, Resource
from yc_watcher.yc.inventory import collect_inventory
```

Then add, below the existing `FakeRpcError` class:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_inventory.py -v`
Expected: the 4 new tests FAIL — `collect_inventory` doesn't accept `billing_account_id`/`tz` yet, and `inventory_module.fetch_daily_expense` doesn't exist to monkeypatch.

- [ ] **Step 3: Wire billing into `collect_inventory`**

Replace `src/yc_watcher/yc/inventory.py` with:

```python
"""Runs every fetcher for one folder and assembles an ``InventorySnapshot``.

This is the single place where the blocking gRPC fetchers are pushed onto worker
threads and awaited together; a failure in one fetcher is captured on its group
and never cancels the rest. The billing fetch rides along in the same gather,
under the same isolation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from yc_watcher.errors import describe_error
from yc_watcher.models import DailyExpense, InventorySnapshot, ResourceGroup
from yc_watcher.yc.billing import fetch_daily_expense
from yc_watcher.yc.fetchers import FETCHERS

log = logging.getLogger(__name__)


async def collect_inventory(
    client,
    fetchers=FETCHERS,
    now: datetime | None = None,
    billing_account_id: str = "",
    tz: ZoneInfo = ZoneInfo("UTC"),
) -> InventorySnapshot:
    resolved_now = now or datetime.now(timezone.utc)

    async def run(spec) -> ResourceGroup:
        try:
            resources = await asyncio.to_thread(spec.fetch, client)
            return ResourceGroup(spec.key, spec.title, tuple(resources))
        except Exception as error:
            log.exception("fetcher %s failed", spec.key)
            return ResourceGroup(spec.key, spec.title, (), error=describe_error(error))

    async def run_billing() -> DailyExpense:
        local_now = resolved_now.astimezone(tz)
        day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            return await asyncio.to_thread(
                fetch_daily_expense, client, billing_account_id, day_start, local_now
            )
        except Exception as error:
            log.exception("daily expense fetch failed")
            return DailyExpense(error=describe_error(error))

    *groups, daily_expense = await asyncio.gather(
        *(run(spec) for spec in fetchers), run_billing()
    )
    return InventorySnapshot(client.folder_id, resolved_now, tuple(groups), daily_expense)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_inventory.py -v`
Expected: PASS (all tests, old and new — the pre-existing tests still pass because their `FakeClient` lacking `.stub()` makes the real `fetch_daily_expense` raise `AttributeError`, which `run_billing` catches into a failed `DailyExpense` they never inspect)

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/yc/inventory.py tests/test_inventory.py
git commit -m "Fetch today's spend alongside the resource inventory"
```

---

### Task 5: Show the spend line in the report

**Files:**
- Modify: `src/yc_watcher/telegram/formatting.py`
- Test: `tests/test_formatting.py`

**Interfaces:**
- Consumes: `InventorySnapshot.daily_expense` (Task 1).
- Produces: `format_snapshot` output gains one line after `Total resources`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_formatting.py`, update the imports and the `_snapshot` helper:

```python
from datetime import datetime, timezone
from decimal import Decimal

from yc_watcher.models import DailyExpense, InventorySnapshot, Resource, ResourceGroup
from yc_watcher.telegram.formatting import (
    format_failure,
    format_snapshot,
    split_message,
)

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


def _snapshot(groups, daily_expense=None):
    return InventorySnapshot(
        "b1gfolder",
        NOW,
        tuple(groups),
        daily_expense or DailyExpense(amount=Decimal("0"), currency="RUB"),
    )
```

Add new tests:

```python
def test_daily_expense_line_shows_amount_and_currency():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),))],
        daily_expense=DailyExpense(amount=Decimal("123.4"), currency="RUB"),
    )
    assert "Total resources: 1\n💰 Spent today: 123.40 RUB" in format_snapshot(snapshot)


def test_daily_expense_failure_shows_an_inline_note():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),))],
        daily_expense=DailyExpense(error="PERMISSION_DENIED"),
    )
    text = format_snapshot(snapshot)
    assert "💰 Spent today: ⚠️ fetch failed: PERMISSION_DENIED" in text


def test_daily_expense_failure_does_not_trigger_the_counts_trailer():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),))],
        daily_expense=DailyExpense(error="PERMISSION_DENIED"),
    )
    assert "counts above may be incomplete" not in format_snapshot(snapshot)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_formatting.py -v`
Expected: FAIL — `InventorySnapshot(...)` in `_snapshot` is missing the required `daily_expense` argument (`TypeError`), so every test in the file fails at collection/call time.

- [ ] **Step 3: Add the spend line**

In `src/yc_watcher/telegram/formatting.py`, add a helper next to `_resource_line` and use it in `format_snapshot`:

```python
def _daily_expense_line(expense: DailyExpense) -> str:
    if expense.failed:
        return f"💰 Spent today: ⚠️ fetch failed: {expense.error}"
    return f"💰 Spent today: {expense.amount:.2f} {expense.currency}"
```

Update the import line and `format_snapshot`'s header:

```python
from yc_watcher.models import DailyExpense, InventorySnapshot, Resource
```

```python
def format_snapshot(snapshot: InventorySnapshot) -> str:
    lines = [
        "📊 Yandex Cloud inventory",
        f"Folder: {snapshot.folder_id}",
        f"Generated: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M')} UTC",
        f"Total resources: {snapshot.total}",
        _daily_expense_line(snapshot.daily_expense),
        "",
    ]
```

(the rest of the function is unchanged)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_formatting.py -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/telegram/formatting.py tests/test_formatting.py
git commit -m "Show today's spend in the inventory report header"
```

---

### Task 6: Thread `billing_account_id` and the schedule's timezone through the scheduler

**Files:**
- Modify: `src/yc_watcher/scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `collect_inventory(client, fetchers=FETCHERS, now=None, billing_account_id="", tz=ZoneInfo("UTC"))` (Task 4).
- Produces: `send_daily_report(bot, yc_client, chat_id, billing_account_id: str = "", tz: ZoneInfo = ZoneInfo("UTC"))`; `build_scheduler(..., billing_account_id: str = "")` — reuses the `ZoneInfo` it already builds from `timezone` for the job's `tz` kwarg.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scheduler.py`, update the imports and `_snapshot` helper:

```python
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
```

Add new tests:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduler.py -v`
Expected: the 2 new tests FAIL — `send_daily_report`/`build_scheduler` don't accept `billing_account_id` yet, and don't pass `tz` through.

- [ ] **Step 3: Wire the parameters through**

In `src/yc_watcher/scheduler.py`:

```python
from zoneinfo import ZoneInfo
```

```python
async def send_daily_report(
    bot: Bot,
    yc_client: YcClient,
    chat_id: int,
    billing_account_id: str = "",
    tz: ZoneInfo = ZoneInfo("UTC"),
) -> None:
    try:
        snapshot = await collect_inventory(
            yc_client, billing_account_id=billing_account_id, tz=tz
        )
        chunks = split_message(format_snapshot(snapshot))
    except Exception as error:
        log.exception("scheduled inventory build failed")
        chunks = [format_failure(str(error))]
    for chunk in chunks:
        try:
            await bot.send_message(chat_id, chunk)
        except TelegramAPIError:
            log.exception("failed to deliver scheduled report to chat_id=%s", chat_id)


def build_scheduler(
    bot: Bot,
    yc_client: YcClient,
    *,
    chat_id: int,
    hour: int,
    minute: int,
    timezone: str,
    billing_account_id: str = "",
) -> AsyncIOScheduler:
    zone = ZoneInfo(timezone)
    scheduler = AsyncIOScheduler(timezone=zone)
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=hour, minute=minute, timezone=zone),
        kwargs={
            "bot": bot,
            "yc_client": yc_client,
            "chat_id": chat_id,
            "billing_account_id": billing_account_id,
            "tz": zone,
        },
        id=DAILY_JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    return scheduler
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/scheduler.py tests/test_scheduler.py
git commit -m "Thread billing_account_id and the schedule zone through the scheduler"
```

---

### Task 7: Pass the configured billing account into the scheduler

**Files:**
- Modify: `src/yc_watcher/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Settings.yc_billing_account_id` (Task 2), `build_scheduler(..., billing_account_id="")` (Task 6).

- [ ] **Step 1: Write the failing test**

In `tests/test_app.py`, add `yc_billing_account_id="acc-1"` to the `_settings()` fixture:

```python
def _settings():
    return SimpleNamespace(
        log_level="INFO",
        yc_sa_key_file="/secrets/sa-key.json",
        yc_folder_id="b1gfolder",
        yc_billing_account_id="acc-1",
        telegram_bot_token=SimpleNamespace(get_secret_value=lambda: "123:abc"),
        allowed_user_ids=frozenset({42}),
        telegram_chat_id=555,
        schedule_hour=9,
        schedule_minute=30,
        schedule_timezone="UTC",
    )
```

Add a new test:

```python
async def test_run_builds_the_scheduler_with_the_billing_account_id(patched):
    settings = _settings()
    await app_module.run(settings)
    assert (
        app_module.build_scheduler.call_args.kwargs["billing_account_id"]
        == settings.yc_billing_account_id
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_app.py -v`
Expected: `test_run_builds_the_scheduler_with_the_billing_account_id` FAILS — `run()` doesn't pass `billing_account_id` to `build_scheduler` yet, so the kwarg is absent from `call_args.kwargs`.

- [ ] **Step 3: Pass it through**

In `src/yc_watcher/app.py`, add the new kwarg to the existing `build_scheduler(...)` call:

```python
    scheduler = build_scheduler(
        bot,
        yc_client,
        chat_id=settings.telegram_chat_id,
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.schedule_timezone,
        billing_account_id=settings.yc_billing_account_id,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_app.py -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 5: Commit**

```bash
git add src/yc_watcher/app.py tests/test_app.py
git commit -m "Pass the configured billing account into the scheduler"
```

---

### Task 8: Full suite sanity pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass, no warnings about unawaited coroutines or unused fixtures.

- [ ] **Step 2: Confirm nothing else constructs `InventorySnapshot` positionally**

Run: `grep -rn "InventorySnapshot(" src tests`
Expected: every call site either uses the 4-argument form (`daily_expense` included) or goes through `collect_inventory`. If anything is missed, fix it before closing out the plan.
