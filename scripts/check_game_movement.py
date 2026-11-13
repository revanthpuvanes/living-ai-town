import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_game_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(TEST_DB)
            )
        )

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

from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import (
    get_world_state,
    initialize_world,
    record_move,
)
from app.db.snapshots import create_snapshot, verify_replay


initialize_world()

initial = get_world_state()
assert initial["tick"] == 0
assert initial["state"]["characters"]["emma"]["location"] == "bakery"

result = record_move(
    uuid4(),
    "emma",
    "square",
    3,
)

assert result["accepted"], result

world = get_world_state()
emma = world["state"]["characters"]["emma"]

assert world["tick"] == 0
assert emma["location"] == "bakery"
assert emma["activity"] == "walking"
assert emma["movement"] == {
    "from": "bakery",
    "to": "square",
    "start_tick": 0,
    "duration_ticks": 3,
}

print("TICK 0: Emma started walking")


for expected_tick in (1, 2):
    advance_tick_once(uuid4())

    world = get_world_state()
    emma = world["state"]["characters"]["emma"]

    assert world["tick"] == expected_tick
    assert emma["location"] == "bakery"
    assert emma["activity"] == "walking"
    assert emma["movement"] is not None

    progress = (
        world["tick"] - emma["movement"]["start_tick"]
    ) / emma["movement"]["duration_ticks"]

    print(
        f"TICK {expected_tick}: "
        f"Emma walking, progress={progress:.0%}"
    )


advance_tick_once(uuid4())

world = get_world_state()
emma = world["state"]["characters"]["emma"]

assert world["tick"] == 3
assert emma["location"] == "square"
assert emma["activity"] == "idle"
assert emma["movement"] is None

print("TICK 3: Emma arrived at town square")

create_snapshot()

replay = verify_replay()

assert (
    replay["full_hash"]
    == replay["snapshot_hash"]
    == replay["live_hash"]
)

print("EVENT REPLAY: PASSED")
print("GAME MOVEMENT INTEGRATION: PASSED")
'''

        subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            check=True,
        )

    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
                """,
                (TEST_DB,),
            )

            conn.execute(
                sql.SQL("DROP DATABASE {}").format(
                    sql.Identifier(TEST_DB)
                )
            )

        print("Temporary database cleaned up")


if __name__ == "__main__":
    main()
