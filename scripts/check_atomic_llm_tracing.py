import os
import subprocess
import sys
from uuid import uuid4

import psycopg

ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_atomic_{uuid4().hex[:12]}"
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

        env = {
            **os.environ,
            "DATABASE_URL": TEST_URL,
            "AI_TOWN_ENABLE_LLM": "0",
        }

        subprocess.run(
            [sys.executable, "-m", "scripts.migrate"],
            env=env,
            check=True,
        )

        code = r'''
from uuid import uuid4

from app.db.connection import get_connection
from app.db.conversations import record_conversation
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import initialize_world, record_move
from app.db.snapshots import create_snapshot, verify_replay
from app.llm.client import DialogueGeneration
from app.llm.dialogue import DialogueResponse


initialize_world()

for character in ("emma", "noah"):
    result = record_move(
        uuid4(), character, "square", 3
    )
    assert result["accepted"], result

for _ in range(3):
    advance_tick_once(uuid4())


def generation(source):
    return DialogueGeneration(
        response=DialogueResponse(
            message="Hello from the bakery!",
            emotion="friendly",
        ),
        source=source,
    )


# CASE 1: Successful atomic persistence
action_id = uuid4()

result = record_conversation(
    action_id,
    "emma",
    "noah",
    "Hello from the bakery!",
    llm_generation=generation("mistral"),
)

assert result["accepted"]
assert not result["duplicate"]

with get_connection() as conn:
    row = conn.execute("""
        SELECT e.id, t.event_id, t.source,
               t.speaker, t.listener
        FROM events e
        JOIN llm_traces t
          ON t.action_id = e.action_id
        WHERE e.action_id = %s
    """, (action_id,)).fetchone()

assert row is not None
assert row[0] == row[1]
assert row[2:] == ("mistral", "emma", "noah")

print("ATOMIC EVENT + TRACE: PASSED")


# CASE 2: Force a trace constraint failure
failed_action_id = uuid4()

try:
    record_conversation(
        failed_action_id,
        "noah",
        "emma",
        "This transaction must roll back.",
        llm_generation=generation("invalid_source"),
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Invalid trace source did not fail"
    )

with get_connection() as conn:
    event_count = conn.execute("""
        SELECT COUNT(*) FROM events
        WHERE action_id = %s
    """, (failed_action_id,)).fetchone()[0]

    decision_count = conn.execute("""
        SELECT COUNT(*) FROM decisions
        WHERE action_id = %s
    """, (failed_action_id,)).fetchone()[0]

    trace_count = conn.execute("""
        SELECT COUNT(*) FROM llm_traces
        WHERE action_id = %s
    """, (failed_action_id,)).fetchone()[0]

assert (event_count, decision_count, trace_count) == (0, 0, 0)

print("FORCED TRANSACTION ROLLBACK: PASSED")

create_snapshot()
verify_replay()

print("EVENT REPLAY: PASSED")
print("ATOMIC LLM TRACING: PASSED")
'''

        subprocess.run(
            [sys.executable, "-c", code],
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
