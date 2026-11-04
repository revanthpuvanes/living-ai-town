import os
import subprocess
import sys

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = "ai_town_conversation_check"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB,),
        ).fetchone()
        if exists:
            raise RuntimeError("Temporary database already exists")
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

from app.db.repository import (
    initialize_world,
    record_move,
    get_world_state,
)
from app.db.idempotent_ticks import advance_tick_once
from app.db.conversations import (
    record_conversation,
    get_recent_conversations,
)
from app.db.snapshots import create_snapshot, verify_replay
from app.engine.world import InvalidAction

initialize_world()

for character in ("emma", "noah"):
    result = record_move(
        uuid4(), character, "square", 3
    )
    assert result["accepted"]

for _ in range(3):
    advance_tick_once(uuid4())

world = get_world_state()
assert world["tick"] == 3

for character in ("emma", "noah"):
    assert world["state"]["characters"][character]["location"] == "square"

action_id = uuid4()

first = record_conversation(
    action_id,
    "emma",
    "noah",
    "Good morning, Noah!",
    expected_tick=world["tick"],
    expected_state_hash=world["state_hash"],
)
assert first["accepted"] and not first["duplicate"]

second = record_conversation(
    action_id,
    "emma",
    "noah",
    "Good morning, Noah!",
    expected_tick=world["tick"],
    expected_state_hash=world["state_hash"],
)
assert second["accepted"] and second["duplicate"]
assert second["event_id"] == first["event_id"]

try:
    record_conversation(
        action_id, "emma", "noah", "Different message"
    )
except InvalidAction:
    pass
else:
    raise AssertionError("Payload reuse was not rejected")

history = get_recent_conversations("noah")
assert len(history) == 1
assert history[0]["message"] == "Good morning, Noah!"

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

print("CONVERSATION PERSISTENCE: PASSED")
print("IDEMPOTENT RETRY: PASSED")
print("PAYLOAD REUSE PROTECTION: PASSED")
print("CONVERSATION RETRIEVAL: PASSED")
print("WORLD HASH UNCHANGED: PASSED")
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
