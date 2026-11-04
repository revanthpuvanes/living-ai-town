from contextlib import contextmanager
from hashlib import sha256

from app.db.connection import get_connection


def interaction_lock_key(speaker, listener, day):
    pair = ":".join(sorted((speaker, listener)))
    value = f"ai-town:interaction:{day}:{pair}"

    digest = sha256(value.encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=True,
    )


@contextmanager
def try_interaction_lock(speaker, listener, day):
    key = interaction_lock_key(speaker, listener, day)

    # Session-level lock: held across separate database
    # transactions used by context, budget and recording.
    with get_connection() as conn:
        conn.autocommit = True

        acquired = conn.execute(
            "SELECT pg_try_advisory_lock(%s)",
            (key,),
        ).fetchone()[0]

        try:
            yield acquired
        finally:
            if acquired:
                released = conn.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (key,),
                ).fetchone()[0]

                if not released:
                    raise RuntimeError(
                        "Failed to release interaction lock"
                    )
