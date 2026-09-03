"""Generic driver for Yandex Cloud's page-token list endpoints.

Every ``List`` call in the SDK shares the same shape - request carries a
``page_token``, response carries ``next_page_token`` - so each fetcher describes
only the three parts that differ and lets this helper run the loop.
"""

from typing import Any, Callable, Iterable


def list_all(
    call: Callable[[Any], Any],
    request_factory: Callable[[str | None], Any],
    items_of: Callable[[Any], Iterable[Any]],
) -> list[Any]:
    collected: list[Any] = []
    token: str | None = None
    while True:
        response = call(request_factory(token))
        collected.extend(items_of(response))
        token = getattr(response, "next_page_token", "") or ""
        if not token:
            return collected
