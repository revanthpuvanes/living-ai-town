"""Shared two-minute simulation session state."""

from datetime import datetime, timedelta, timezone

from app.db.connection import get_connection


SESSION_SECONDS = 120


def ensure_session_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_session (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                ends_at TIMESTAMPTZ
            )
        """)
        conn.execute("""
            INSERT INTO demo_session (id, ends_at)
            VALUES (1, NULL)
            ON CONFLICT (id) DO NOTHING
        """)


def get_session():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT ends_at
            FROM demo_session
            WHERE id = 1
        """).fetchone()

    ends_at = row[0] if row else None
    remaining = max(
        0,
        int((ends_at - datetime.now(timezone.utc)).total_seconds() + 0.999),
    ) if ends_at else 0

    return {
        "active": remaining > 0,
        "remaining_seconds": remaining,
    }


def start_session():
    with get_connection() as conn:
        row = conn.execute("""
            UPDATE demo_session
            SET ends_at = NOW() + INTERVAL '120 seconds'
            WHERE id = 1
              AND (ends_at IS NULL OR ends_at <= NOW())
            RETURNING ends_at
        """).fetchone()

    if row is None:
        return get_session()

    return {
        "active": True,
        "remaining_seconds": SESSION_SECONDS,
    }


def stop_session():
    """End the active simulation session immediately."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE demo_session
            SET ends_at = NULL
            WHERE id = 1
        """)

    return {
        "active": False,
        "remaining_seconds": 0,
    }
