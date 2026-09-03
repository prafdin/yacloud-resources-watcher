from types import SimpleNamespace

import pytest

from yc_watcher.models import Resource
from yc_watcher.yc.fetchers import FETCHERS


class FakeStub:
    def __init__(self, pages):
        self._pages = pages
        self.requests = []

    def List(self, request):
        self.requests.append(request)
        return self._pages[request.page_token]


class FakeClient:
    folder_id = "b1gfolder"

    def __init__(self, pages):
        self._stub = FakeStub(pages)
        self.asked = []

    def stub(self, stub_ctor):
        self.asked.append(stub_ctor)
        return self._stub


def _page(attr, items, next_token=""):
    return SimpleNamespace(**{attr: items, "next_page_token": next_token})


SPECS = {spec.key: spec for spec in FETCHERS}


def test_registry_has_eleven_unique_keys():
    assert len(FETCHERS) == 11 == len({spec.key for spec in FETCHERS})


@pytest.mark.parametrize("spec", FETCHERS, ids=lambda s: s.key)
def test_fetcher_maps_items_to_resources(spec):
    attr = spec.items_attr
    client = FakeClient({"": _page(attr, [SimpleNamespace(id="r1", name="alpha")])})
    assert spec.fetch(client) == [Resource(id="r1", name="alpha")]


@pytest.mark.parametrize("spec", FETCHERS, ids=lambda s: s.key)
def test_fetcher_scopes_request_to_folder(spec):
    attr = spec.items_attr
    client = FakeClient({"": _page(attr, [])})
    spec.fetch(client)
    assert client._stub.requests[0].folder_id == "b1gfolder"


def test_fetcher_falls_back_to_id_when_name_is_blank():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="")])})
    assert spec.fetch(client) == [Resource(id="r1", name="r1")]


def test_fetcher_follows_pagination():
    spec = SPECS["compute_instances"]
    attr = spec.items_attr
    client = FakeClient(
        {
            "": _page(attr, [SimpleNamespace(id="r1", name="a")], next_token="p2"),
            "p2": _page(attr, [SimpleNamespace(id="r2", name="b")]),
        }
    )
    assert [r.id for r in spec.fetch(client)] == ["r1", "r2"]
