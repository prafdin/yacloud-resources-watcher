"""Renders an inventory snapshot as plain Telegram message text.

Deliberately emits no Markdown or HTML so arbitrary resource names never need
escaping; long reports are cut into sendable chunks on line boundaries.
"""

from yc_watcher.models import InventorySnapshot

TELEGRAM_LIMIT = 4096
INCOMPLETE_NOTE = (
    "Note: one or more resource types could not be listed; "
    "counts above may be incomplete."
)


def format_snapshot(snapshot: InventorySnapshot) -> str:
    lines = [
        "📊 Yandex Cloud inventory",
        f"Folder: {snapshot.folder_id}",
        f"Generated: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M')} UTC",
        f"Total resources: {snapshot.total}",
        "",
    ]
    if snapshot.is_empty:
        lines.append("✅ No resources found in this folder.")
        return "\n".join(lines)
    sections = []
    for group in snapshot.groups:
        if group.failed:
            sections.append(f"{group.title} — ⚠️ fetch failed: {group.error}")
            continue
        body = "\n".join(f"  • {resource.name}" for resource in group.resources) or "  (none)"
        sections.append(f"{group.title} ({group.count})\n{body}")
    lines.append("\n\n".join(sections))
    if snapshot.any_failed:
        lines.extend(["", INCOMPLETE_NOTE])
    return "\n".join(lines)


def format_failure(reason: str) -> str:
    return f"⚠️ Could not build the inventory report: {reason}"


def split_message(text: str, limit: int = 4000) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.split("\n"):
        addition = len(line) + (1 if current else 0)
        if current and size + addition > limit:
            chunks.append("\n".join(current))
            current, size = [], 0
            addition = len(line)
        current.append(line)
        size += addition
    if current:
        chunks.append("\n".join(current))
    return chunks
