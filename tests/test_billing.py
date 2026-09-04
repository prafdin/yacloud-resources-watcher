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


def test_treats_an_unset_expense_as_zero():
    response = FolderUsageReportResponse(currency=RUB)
    client = FakeClient(FakeStub(response))
    result = fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
    assert result == DailyExpense(amount=Decimal("0"), currency="RUB")


def test_propagates_errors_from_the_stub_without_catching_them():
    client = FakeClient(FakeStub(raises=RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        fetch_daily_expense(client, "acc-1", DAY_START, DAY_END)
