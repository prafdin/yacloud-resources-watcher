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
