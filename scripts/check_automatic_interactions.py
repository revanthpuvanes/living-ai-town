import os
import subprocess
import sys
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_interactions_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {TEST_DB}")

    try:
        with open("db/init/001_schema.sql") as file:
            schema = file.read()

        with psycopg.connect(TEST_URL) as conn:
            conn.execute(schema)

        env = {**os.environ, "DATABASE_URL": TEST_URL}

        subprocess.run(
            [sys.executable, "-m", "scripts.migrate"],
            env=env,
            check=True,
        )

        test_code = """
from uuid import uuid4

from app.agents.interactions import run_interactions
from app.db.conversations import get_recent_conversations
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import (
    get_world_state,
    initialize_world,
    record_move,
)
from app.db.snapshots import create_snapshot, verify_replay
from app.db.connection import get_connection


initialize_world()

# Emma and Noah travel to the square.
for character in ("emma", "noah"):
    result = record_move(
        uuid4(),
        character,
        "square",
        3,
    )
    assert result["accepted"]

# They cannot talk while walking.
assert run_interactions(execute=False) == []
print("MOVEMENT VALIDATION: PASSED")

for _ in range(3):
    advance_tick_once(uuid4())

world = get_world_state()
assert world["tick"] == 3

# First automatic interaction.
first = run_interactions(execute=True)
assert len(first) == 1
assert first[0].speaker == "emma"
assert first[0].listener == "noah"
assert first[0].result["accepted"]
assert not first[0].result["duplicate"]
print("AUTOMATIC CONVERSATION: PASSED")

# Retry the same logical interaction.
second = run_interactions(execute=True)
assert len(second) == 1
assert second[0].result["accepted"]
assert second[0].result["duplicate"]
assert (
    second[0].result["event_id"]
    == first[0].result["event_id"]
)
print("IDEMPOTENT RETRY: PASSED")

history = get_recent_conversations("noah")
assert len(history) == 1
assert history[0]["speaker"] == "emma"
print("CONVERSATION HISTORY: PASSED")

# Confirm exactly one durable conversation event.
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM events "
            "WHERE type = 'CONVERSATION_SPOKEN'"
        )
        assert cur.fetchone()[0] == 1

print("NO DUPLICATE EVENTS: PASSED")

# Conversation events do not alter physical world state.
after = get_world_state()
assert after["tick"] == world["tick"]
assert after["state_hash"] == world["state_hash"]

create_snapshot()
replay = verify_replay()

assert (
    replay["full_hash"]
    == replay["snapshot_hash"]
    == replay["live_hash"]
)

print("EVENT REPLAY: PASSED")
"""

        subprocess.run(
            [sys.executable, "-c", test_code],
            env=env,
            check=True,
        )

    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
            """, (TEST_DB,))
            conn.execute(f"DROP DATABASE {TEST_DB}")

        print("Temporary database cleaned up")


if __name__ == "__main__":
    main()
