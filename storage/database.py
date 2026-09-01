"""SQLite persistence for notifications."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from storage.models import Notification

SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pending_unacknowledged
ON pending_notifications(acknowledged, reminder_sent);

CREATE INDEX IF NOT EXISTS idx_pending_chat_id
ON pending_notifications(chat_id);

CREATE TABLE IF NOT EXISTS notification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    resources_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_history_sent_at
ON notification_history(sent_at DESC);
"""


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _dump_dt(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        """Create database file and tables if they do not exist."""
        directory = os.path.dirname(os.path.abspath(self.db_path))
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def save_pending_notification(
        self, message_id: int, chat_id: int, sent_at: datetime
    ) -> int:
        """Save a new pending notification and return its id."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO pending_notifications (message_id, chat_id, sent_at)
                VALUES (?, ?, ?)
                """,
                (message_id, chat_id, _dump_dt(sent_at)),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def get_unacknowledged_notifications(self) -> list[Notification]:
        """Return all unacknowledged notifications."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, message_id, chat_id, sent_at, acknowledged, reminder_sent
                FROM pending_notifications
                WHERE acknowledged = 0
                ORDER BY sent_at ASC
                """
            )
            rows = await cursor.fetchall()
        return [
            Notification(
                id=row["id"],
                message_id=row["message_id"],
                chat_id=row["chat_id"],
                sent_at=_parse_dt(row["sent_at"]),
                acknowledged=bool(row["acknowledged"]),
                reminder_sent=bool(row["reminder_sent"]),
            )
            for row in rows
        ]

    async def get_latest_pending_notification(self, chat_id: int) -> Notification | None:
        """Return the most recent unacknowledged notification for a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, message_id, chat_id, sent_at, acknowledged, reminder_sent
                FROM pending_notifications
                WHERE chat_id = ? AND acknowledged = 0
                ORDER BY sent_at DESC, id DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return Notification(
            id=row["id"],
            message_id=row["message_id"],
            chat_id=row["chat_id"],
            sent_at=_parse_dt(row["sent_at"]),
            acknowledged=bool(row["acknowledged"]),
            reminder_sent=bool(row["reminder_sent"]),
        )

    async def acknowledge_notification(self, message_id: int, chat_id: int) -> bool:
        """Mark a notification as acknowledged by message and chat ids."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE pending_notifications
                SET acknowledged = 1
                WHERE message_id = ? AND chat_id = ? AND acknowledged = 0
                """,
                (message_id, chat_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def acknowledge_latest_notification(self, chat_id: int) -> bool:
        """Mark the most recent pending notification for a chat as acknowledged."""
        notification = await self.get_latest_pending_notification(chat_id)
        if notification is None:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE pending_notifications
                SET acknowledged = 1
                WHERE id = ?
                """,
                (notification.id,),
            )
            await db.execute(
                """
                UPDATE notification_history
                SET acknowledged_at = ?
                WHERE id = (
                    SELECT id FROM notification_history
                    WHERE acknowledged_at IS NULL
                    ORDER BY sent_at DESC, id DESC
                    LIMIT 1
                )
                """,
                (_dump_dt(datetime.now(timezone.utc)),),
            )
            await db.commit()
        return True

    async def mark_reminder_sent(self, notification_id: int) -> None:
        """Mark that a reminder was sent for this notification."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE pending_notifications
                SET reminder_sent = 1
                WHERE id = ?
                """,
                (notification_id,),
            )
            await db.commit()

    async def save_notification_history(
        self, sent_at: datetime, resources_count: int
    ) -> None:
        """Save a sent notification to history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO notification_history (sent_at, resources_count)
                VALUES (?, ?)
                """,
                (_dump_dt(sent_at), resources_count),
            )
            await db.commit()

    async def get_total_reports_count(self) -> int:
        """Return total number of reports sent."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM notification_history")
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def get_pending_count(self) -> int:
        """Return count of unacknowledged notifications."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM pending_notifications
                WHERE acknowledged = 0
                """
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0
