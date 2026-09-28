"""Fetches how much has been spent on the folder's billing account on one UTC day.

The usage report API treats both request dates as inclusive whole UTC days, so
the same day is sent as start and end.

Mirrors ``FetcherSpec.fetch`` from ``yc/fetchers.py``: one stub, one request,
one response. This raises on failure and leaves catching it to the caller,
the same division of labor ``collect_inventory`` already has with fetchers.
"""

from datetime import date, datetime, time, timezone
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


def fetch_daily_expense(client, billing_account_id: str, day: date) -> DailyExpense:
    stub = client.stub(ConsumptionCoreServiceStub)
    stamp = Timestamp()
    stamp.FromDatetime(datetime.combine(day, time(), tzinfo=timezone.utc))
    request = UsageReportRequest(
        billing_account_id=billing_account_id,
        start_date=stamp,
        end_date=stamp,
        folder_ids=[client.folder_id],
    )
    response = stub.GetFolderUsageReport(request)
    return DailyExpense(
        amount=Decimal(response.expense.value or "0"), currency=Currency.Name(response.currency)
    )
