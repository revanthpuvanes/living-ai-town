import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_concurrent_{uuid4().hex[:12]}"
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

        run_code('''
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.db.conversations import record_conversation
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import initialize_world, record_move
from app.db.connection import get_connection
from app.db.snapshots import create_snapshot, verify_replay

initialize_world()

for character in ("emma", "noah"):
    result = record_move(
        uuid4(), character, "square", 3
    )
    assert result["accepted"], result

for _ in range(3):
    advance_tick_once(uuid4())

def worker(_):
    return record_conversation(
        uuid4(),
        "emma",
        "noah",
        "Good morning, Noah!",
        expected_tick=3,
        auto_pair_day="0:emma:noah",
    )

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(worker, range(2)))

print("Concurrent results:", results)

assert all(result["accepted"] for result in results)
assert sum(not result["duplicate"] for result in results) == 1
assert sum(result["duplicate"] for result in results) == 1

with get_connection() as conn:
    rows = conn.execute("""
        SELECT id, payload->>'auto_pair_day'
        FROM events
        WHERE type = 'CONVERSATION_SPOKEN'
    """).fetchall()

assert len(rows) == 1, rows
assert rows[0][1] == "0:emma:noah"
print("CONCURRENT UNIQUENESS: PASSED")

for _ in range(2):
    result = record_conversation(
        uuid4(),
        "emma",
        "noah",
        "A manual conversation",
    )
    assert result["accepted"], result

with get_connection() as conn:
    count = conn.execute("""
        SELECT count(*)
        FROM events
        WHERE type = 'CONVERSATION_SPOKEN'
    """).fetchone()[0]

assert count == 3, count
print("MANUAL CONVERSATIONS UNRESTRICTED: PASSED")

create_snapshot()
verify_replay()
print("EVENT REPLAY: PASSED")
''', env)

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
