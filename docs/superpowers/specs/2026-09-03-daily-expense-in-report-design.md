# Daily expense in the inventory report

## Purpose

The Telegram inventory report currently lists resources only. Add how much
money was spent on the folder's billing account so far today, so the report
doubles as a quick cost check.

## Data source

Yandex Cloud's Billing SDK exposes
`ConsumptionCoreService.GetFolderUsageReport` (in
`yandex.cloud.billing.usage_records.v1`), which accepts a
`billing_account_id`, a `[start_date, end_date)` window, and `folder_ids`, and
returns a `FolderUsageReportResponse` carrying `expense` (a `StringDecimal`,
already net of discounts/credits — what was actually charged) and `currency`
(an enum: `RUB`, `USD`, `KZT`, `EUR`).

"Today" is the window from local midnight (in `schedule_timezone`) to the
moment the report is generated.

## Configuration

`Settings` (`config.py`) gains a required field:

```python
yc_billing_account_id: str
```

No default — matches the treatment of `yc_folder_id`. Deployments must set
`YC_BILLING_ACCOUNT_ID` before upgrading.

## Data model (`models.py`)

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

`InventorySnapshot` gains a required field `daily_expense: DailyExpense`.

## Fetching (`yc/billing.py`, new module)

```python
def fetch_daily_expense(
    client, billing_account_id: str, day_start: datetime, day_end: datetime
) -> DailyExpense:
    ...
```

Builds a `UsageReportRequest(billing_account_id=..., start_date=..., end_date=...,
folder_ids=[client.folder_id])` (dates converted to `google.protobuf.Timestamp`
via `Timestamp.FromDatetime`, which handles timezone-aware datetimes), calls
`GetFolderUsageReport` through `client.stub(ConsumptionCoreServiceStub)`, and
returns `DailyExpense(amount=Decimal(response.expense.value),
currency=Currency.Name(response.currency))`.

This function raises on failure — the caller is responsible for catching and
turning the error into `DailyExpense(error=...)`, the same division of labor
`FetcherSpec.fetch` has today (it raises; `collect_inventory` catches).

## Collection (`yc/inventory.py`)

`collect_inventory` gains two parameters: `billing_account_id: str` and
`tz: ZoneInfo`. It computes the day window from `now` (or
`datetime.now(timezone.utc)` if `now` is omitted) converted into `tz`,
truncated to midnight for `day_start`, using the (tz-converted) `now` itself
as `day_end`.

The billing fetch runs inside the same `asyncio.gather` as the resource
fetchers, wrapped in the same try/except pattern used for each `FetcherSpec`:
success populates `DailyExpense`, any exception is caught, logged, and turned
into `DailyExpense(error=describe_error(error))` — a billing failure never
aborts the resource fetchers or the report.

## Report format (`telegram/formatting.py`)

One new line in the header, immediately after `Total resources`:

```
💰 Spent today: 123.45 RUB
```

or, if the billing fetch failed:

```
💰 Spent today: ⚠️ fetch failed: PERMISSION_DENIED: ...
```

`amount` is formatted to two decimal places. The existing
`INCOMPLETE_NOTE` trailer ("counts above may be incomplete") is unchanged —
it describes resource counts; a billing failure is already visible inline
and is a different kind of incompleteness.

## Wiring (`scheduler.py`, `app.py`)

`send_daily_report` (or `build_scheduler`, whichever ends up holding the
call) passes `settings.yc_billing_account_id` and `settings.tzinfo` through
to `collect_inventory`.

## Out of scope

- Historical/non-daily spend windows.
- Multiple billing accounts or clouds.
- Currency conversion or symbol formatting — the currency code is shown as
  returned by the API.
- Auto-discovering the billing account via `ListBillingAccounts`.
