from datetime import datetime, timezone

import grpc

from yc_watcher.models import Resource
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
