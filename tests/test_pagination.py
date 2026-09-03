from types import SimpleNamespace

from yc_watcher.yc.pagination import list_all


class FakeList:
    def __init__(self, pages):
        self._pages = pages
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        items, next_token = self._pages[request["token"]]
        return SimpleNamespace(items=items, next_page_token=next_token)


def _request_factory(token):
    return {"token": token or ""}


def _items_of(response):
    return response.items


def test_single_page_makes_one_call():
    call = FakeList({"": (["a", "b"], "")})
    result = list_all(call, _request_factory, _items_of)
    assert result == ["a", "b"]
    assert len(call.requests) == 1


def test_multiple_pages_are_concatenated_in_order():
    call = FakeList({"": (["a", "b"], "p2"), "p2": (["c"], "p3"), "p3": (["d", "e"], "")})
    assert list_all(call, _request_factory, _items_of) == ["a", "b", "c", "d", "e"]


def test_empty_result_returns_empty_list():
    call = FakeList({"": ([], "")})
    assert list_all(call, _request_factory, _items_of) == []
