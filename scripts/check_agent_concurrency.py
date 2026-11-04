import os
import subprocess
import sys

import psycopg


ADMIN_URL = "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
TEST_DB = "ai_town_agent_concurrency_check"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (TEST_DB,),
            )
            if cur.fetchone():
                raise RuntimeError(
                    f"{TEST_DB} already exists; refusing to overwrite it"
                )
            cur.execute(f"CREATE DATABASE {TEST_DB}")

    print("Temporary concurrency database created", flush=True)

    try:
        with open("db/init/001_schema.sql") as schema:
            sql = schema.read()

        with psycopg.connect(TEST_URL) as conn:
            conn.execute(sql)

        env = {**os.environ, "DATABASE_URL": TEST_URL}

        subprocess.run(
            [sys.executable, "-m", "scripts.migrate"],
            env=env,
            check=True,
        )

        setup = """
from uuid import uuid4

from app.db.repository import (
    initialize_world,
    record_move,
    get_world_state,
)
from app.db.idempotent_ticks import advance_tick_once
initialize_world()

result = record_move(
    action_id=uuid4(),
    character_id="emma",
    destination="square",
    duration_ticks=3,
)
assert result["accepted"]

for _ in range(3):
    advance_tick_once(uuid4())

world = get_world_state()
emma = world["state"]["characters"]["emma"]

assert world["tick"] == 3
assert emma["location"] == "square"
assert emma["activity"] == "idle"
assert emma["movement"] is None

print("TEST SETUP: Emma is idle at square, tick 3", flush=True)
"""
        subprocess.run(
            [sys.executable, "-c", setup],
            env=env,
            check=True,
        )

        worker_code = """
from app.agents.runner import run_agent_once
from app.engine.world import InvalidAction

try:
    result = run_agent_once("emma")
    print(result, flush=True)
except InvalidAction as exc:
    if "Stale observation" not in str(exc):
        raise
    print(f"STALE: {exc}", flush=True)
"""

        workers = [
            subprocess.Popen(
                [sys.executable, "-c", worker_code],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]

        for index, worker in enumerate(workers, start=1):
            stdout, stderr = worker.communicate(timeout=20)
            print(f"Worker {index}: {stdout.strip()}")
            if stderr:
                print(stderr)
            assert worker.returncode == 0

        with psycopg.connect(TEST_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM events
                    WHERE actor = 'emma'
                      AND type = 'MOVE_STARTED'
                      AND payload->>'to' = 'bakery'
                """)
                event_count = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*)
                    FROM decisions
                    WHERE agent = 'emma'
                      AND validator_result = 'accepted'
                      AND raw_output->>'destination' = 'bakery'
                """)
                accepted_count = cur.fetchone()[0]

                cur.execute("""
                    SELECT state
                    FROM world_state
                    WHERE id = 1
                """)
                state = cur.fetchone()[0]

        assert event_count == 1, event_count
        assert accepted_count == 1, accepted_count

        emma = state["characters"]["emma"]
        assert emma["activity"] == "walking"
        assert emma["movement"]["to"] == "bakery"

        print("Accepted move events:", event_count)
        print("Accepted decisions:", accepted_count)
        print("CONCURRENT AGENT EXECUTION: PASSED")

    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                """, (TEST_DB,))
                cur.execute(f"DROP DATABASE {TEST_DB}")

        print("Temporary database cleaned up")


if __name__ == "__main__":
    main()
