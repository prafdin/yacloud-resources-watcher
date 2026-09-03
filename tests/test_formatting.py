from datetime import datetime, timezone

from yc_watcher.models import DailyExpense, InventorySnapshot, Resource, ResourceGroup
from yc_watcher.telegram.formatting import (
    format_failure,
    format_snapshot,
    split_message,
)

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)


def _snapshot(groups):
    return InventorySnapshot("b1gfolder", NOW, tuple(groups), DailyExpense())


def test_header_carries_folder_time_and_total():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),))]
    )
    text = format_snapshot(snapshot)
    assert "Folder: b1gfolder" in text
    assert "Generated: 2026-09-03 09:00 UTC" in text
    assert "Total resources: 1" in text


def test_populated_section_lists_resource_names():
    snapshot = _snapshot(
        [
            ResourceGroup(
                "compute",
                "🖥 Compute instances",
                (Resource("i1", "web-1"), Resource("i2", "web-2")),
            )
        ]
    )
    assert "🖥 Compute instances (2)\n  • web-1\n  • web-2" in format_snapshot(snapshot)


def test_empty_section_is_omitted_from_report():
    snapshot = _snapshot(
        [
            ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),)),
            ResourceGroup("disks", "💾 Disks", ()),
        ]
    )
    assert "Disks" not in format_snapshot(snapshot)


def test_failed_section_shows_error_and_no_body():
    snapshot = _snapshot(
        [
            ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),)),
            ResourceGroup("func", "⚡ Serverless functions", (), error="PERMISSION_DENIED"),
        ]
    )
    text = format_snapshot(snapshot)
    assert "⚡ Serverless functions — ⚠️ fetch failed: PERMISSION_DENIED" in text
    assert "(none)" not in text


def test_any_failure_appends_incomplete_counts_trailer():
    snapshot = _snapshot(
        [ResourceGroup("func", "⚡ Serverless functions", (), error="boom")]
    )
    assert "counts above may be incomplete" in format_snapshot(snapshot)


def test_clean_report_has_no_trailer():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "web-1"),))]
    )
    assert "counts above may be incomplete" not in format_snapshot(snapshot)


def test_empty_folder_shows_dedicated_line_and_no_sections():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", ()), ResourceGroup("disks", "💾 Disks", ())]
    )
    text = format_snapshot(snapshot)
    assert "✅ No resources found in this folder." in text
    assert "🖥 Compute instances" not in text


def test_format_failure_wraps_reason():
    assert format_failure("token expired") == (
        "⚠️ Could not build the inventory report: token expired"
    )


def test_split_message_keeps_short_text_as_single_chunk():
    assert split_message("one\ntwo\nthree") == ["one\ntwo\nthree"]


def test_split_message_breaks_long_text_on_line_boundaries():
    body = "\n".join(f"line-{n}" for n in range(1000))
    chunks = split_message(body, limit=200)
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert "\n".join(chunks) == body


def test_split_message_preserves_order():
    body = "\n".join(f"line-{n}" for n in range(50))
    chunks = split_message(body, limit=60)
    assert chunks[0].startswith("line-0")


def test_instance_line_shows_running_status():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "capusta", "running"),))]
    )
    assert "  • capusta — running" in format_snapshot(snapshot)


def test_instance_line_shows_stopped_status():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "capusta", "stopped"),))]
    )
    assert "  • capusta — stopped" in format_snapshot(snapshot)


def test_resource_without_status_has_no_status_suffix():
    snapshot = _snapshot(
        [ResourceGroup("buckets", "🪣 Object Storage buckets", (Resource("b1", "my-bucket"),))]
    )
    assert "my-bucket —" not in format_snapshot(snapshot)
