import os
import subprocess
import sys
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_cooldown_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def run_code(code, env):
    subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        check=True,
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

        run_code("""
from uuid import uuid4

from app.agents.interactions import run_interactions
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import initialize_world, record_move
from app.db.snapshots import create_snapshot

initialize_world()

for character in ("emma", "noah"):
    assert record_move(
        uuid4(), character, "square", 3
    )["accepted"]

for _ in range(3):
    advance_tick_once(uuid4())

first = run_interactions(execute=True)
assert len(first) == 1
assert first[0].result["accepted"]
assert not first[0].result["duplicate"]

assert run_interactions(execute=True) == []
print("SAME-TICK COOLDOWN: PASSED")

advance_tick_once(uuid4())
assert run_interactions(execute=True) == []
print("NEXT-TICK COOLDOWN: PASSED")

create_snapshot()
""", env)

        # A fresh Python process must see the persisted cooldown.
        run_code("""
from app.agents.interactions import run_interactions
from app.db.repository import get_world_state

assert get_world_state()["tick"] == 4
assert run_interactions(execute=True) == []
print("PROCESS RESTART PERSISTENCE: PASSED")
""", env)

        run_code("""
from uuid import uuid4

from app.agents.interactions import run_interactions
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay
from app.db.connection import get_connection

while get_world_state()["tick"] < 24:
    advance_tick_once(uuid4())

next_day = run_interactions(execute=True)
assert len(next_day) == 1
assert next_day[0].result["accepted"]
assert not next_day[0].result["duplicate"]

with get_connection() as conn:
    count = conn.execute(
        "SELECT count(*) FROM events "
        "WHERE type = 'CONVERSATION_SPOKEN'"
    ).fetchone()[0]

assert count == 2, count
print("NEXT-DAY CONVERSATION: PASSED")
print("EXACTLY TWO CONVERSATION EVENTS: PASSED")

verify_replay()
print("EVENT REPLAY: PASSED")
""", env)

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
