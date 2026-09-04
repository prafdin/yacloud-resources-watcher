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
        amount=Decimal(response.expense.value or "0"), currency=Currency.Name(response.currency)
    )
