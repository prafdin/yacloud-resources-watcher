"""Runs every fetcher for one folder and assembles an ``InventorySnapshot``.

This is the single place where the blocking gRPC fetchers are pushed onto worker
threads and awaited together; a failure in one fetcher is captured on its group
and never cancels the rest.
"""

import asyncio
import logging
from datetime import datetime, timezone

from yc_watcher.errors import describe_error
from yc_watcher.models import InventorySnapshot, ResourceGroup
from yc_watcher.yc.fetchers import FETCHERS

log = logging.getLogger(__name__)


async def collect_inventory(client, fetchers=FETCHERS, now: datetime | None = None) -> InventorySnapshot:
    async def run(spec) -> ResourceGroup:
        try:
            resources = await asyncio.to_thread(spec.fetch, client)
            return ResourceGroup(spec.key, spec.title, tuple(resources))
        except Exception as error:
            log.exception("fetcher %s failed", spec.key)
            return ResourceGroup(spec.key, spec.title, (), error=describe_error(error))

    groups = await asyncio.gather(*(run(spec) for spec in fetchers))
    return InventorySnapshot(
        client.folder_id, now or datetime.now(timezone.utc), tuple(groups)
    )
