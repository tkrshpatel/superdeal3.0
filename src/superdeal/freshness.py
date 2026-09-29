"""Deal freshness and expiry helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def freshness_status(last_seen_at: str, *, now: datetime | None = None,
                     stale_after: timedelta = timedelta(hours=24)) -> str:
    """Return fresh, stale, or future based on the last observation timestamp."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    observed = _parse_timestamp(last_seen_at)
    age = current - observed
    if age.total_seconds() < 0:
        return "future"
    return "fresh" if age <= stale_after else "stale"


def mark_stale_deals(connection: sqlite3.Connection, *, now: datetime | None = None,
                     stale_after: timedelta = timedelta(hours=24)) -> int:
    """Mark active deals stale when they have not been observed recently."""
    current = now or datetime.now(timezone.utc)
    cutoff = current - stale_after
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    cursor = connection.execute(
        """UPDATE deals SET status = 'stale'
           WHERE status = 'active' AND last_seen_at < ?""",
        (cutoff_iso,),
    )
    connection.commit()
    return cursor.rowcount


def expire_stale_deals(connection: sqlite3.Connection, *, now: datetime | None = None,
                       stale_after: timedelta = timedelta(hours=24),
                       expire_after: timedelta = timedelta(days=7)) -> int:
    """Expire stale deals after the configured retention period."""
    current = now or datetime.now(timezone.utc)
    cutoff = current - expire_after
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    cursor = connection.execute(
        """UPDATE deals SET status = 'expired'
           WHERE status IN ('active', 'stale') AND last_seen_at < ?""",
        (cutoff_iso,),
    )
    connection.commit()
    return cursor.rowcount


def deal_freshness(connection: sqlite3.Connection, deal_id: int, *,
                   now: datetime | None = None,
                   stale_after: timedelta = timedelta(hours=24),
                   expire_after: timedelta = timedelta(days=7)) -> dict | None:
    row = connection.execute(
        "SELECT id, status, last_seen_at FROM deals WHERE id = ?", (deal_id,)
    ).fetchone()
    if row is None:
        return None
    status = freshness_status(row["last_seen_at"], now=now, stale_after=stale_after)
    age_seconds = max(
        0.0,
        ((_parse_timestamp(now.isoformat() if now else datetime.now(timezone.utc)) -
          _parse_timestamp(row["last_seen_at"])).total_seconds()),
    )
    effective_status = "expired" if age_seconds > expire_after.total_seconds() else status
    return {
        "deal_id": deal_id,
        "status": effective_status,
        "last_seen_at": row["last_seen_at"],
        "age_hours": round(age_seconds / 3600, 2),
        "stale_after_hours": round(stale_after.total_seconds() / 3600, 2),
        "expire_after_hours": round(expire_after.total_seconds() / 3600, 2),
    }
