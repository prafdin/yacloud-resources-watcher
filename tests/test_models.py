from datetime import datetime, timezone
from decimal import Decimal

from yc_watcher.models import DailyExpense, InventorySnapshot, Resource, ResourceGroup

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


def _group(key="compute", resources=(), error=None):
    return ResourceGroup(key=key, title=key.title(), resources=tuple(resources), error=error)


def test_group_count_reflects_number_of_resources():
    group = _group(resources=[Resource("id1", "a"), Resource("id2", "b")])
    assert group.count == 2


def test_group_without_error_is_not_failed():
    assert _group(resources=[Resource("id1", "a")]).failed is False


def test_group_with_error_is_failed():
    assert _group(error="PERMISSION_DENIED").failed is True


def test_snapshot_total_sums_group_counts():
    snapshot = InventorySnapshot(
        "b1g",
        NOW,
        (_group("a", [Resource("1", "1")]), _group("b", [Resource("2", "2"), Resource("3", "3")])),
        DailyExpense(),
    )
    assert snapshot.total == 3


def test_snapshot_any_failed_is_true_when_a_group_failed():
    snapshot = InventorySnapshot("b1g", NOW, (_group("a"), _group("b", error="boom")), DailyExpense())
    assert snapshot.any_failed is True


def test_snapshot_is_empty_when_no_resources_and_no_failures():
    snapshot = InventorySnapshot("b1g", NOW, (_group("a"), _group("b")), DailyExpense())
    assert snapshot.is_empty is True


def test_snapshot_is_not_empty_when_a_group_failed():
    snapshot = InventorySnapshot("b1g", NOW, (_group("a", error="boom"),), DailyExpense())
    assert snapshot.is_empty is False


def test_resource_is_frozen():
    resource = Resource("id1", "name1")
    try:
        resource.name = "other"
    except AttributeError:
        return
    raise AssertionError("Resource must not allow attribute assignment")


def test_daily_expense_without_error_is_not_failed():
    assert DailyExpense(amount=Decimal("1.00"), currency="RUB").failed is False


def test_daily_expense_with_error_is_failed():
    assert DailyExpense(error="PERMISSION_DENIED").failed is True


def test_daily_expense_defaults_to_no_amount_currency_or_error():
    expense = DailyExpense()
    assert (expense.amount, expense.currency, expense.error) == (None, None, None)
