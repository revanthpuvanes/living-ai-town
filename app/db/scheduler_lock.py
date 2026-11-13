"""Prevent concurrent Living AI Town scheduler cycles."""

from contextlib import contextmanager

from app.db.connection import get_connection


# Fixed application-specific PostgreSQL advisory lock key.
SCHEDULER_LOCK_KEY = 724193860215


@contextmanager
def try_scheduler_lock():
    """Acquire a non-blocking lock for the entire scheduler cycle."""
    with get_connection() as conn:
        conn.autocommit = True

        acquired = conn.execute(
            "SELECT pg_try_advisory_lock(%s)",
            (SCHEDULER_LOCK_KEY,),
        ).fetchone()[0]

        try:
            yield acquired
        finally:
            if acquired:
                released = conn.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (SCHEDULER_LOCK_KEY,),
                ).fetchone()[0]

                if not released:
                    raise RuntimeError(
                        "Failed to release scheduler lock"
                    )
