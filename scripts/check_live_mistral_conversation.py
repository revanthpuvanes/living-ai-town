import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)

TEST_DB = f"ai_town_live_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def load_local_env():
    values = {}

    for line in Path(".env").read_text().splitlines():
        if not line or line.startswith("#"):
            continue

        key, separator, value = line.partition("=")

        if separator:
            values[key] = value

    return values


def main():
    local_env = load_local_env()

    if not local_env.get("MISTRAL_API_KEY"):
        raise RuntimeError("Missing Mistral API key")

    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {TEST_DB}")

    try:
        schema = Path("db/init/001_schema.sql").read_text()

        with psycopg.connect(TEST_URL) as conn:
            conn.execute(schema)

        env = {
            **os.environ,
            "DATABASE_URL": TEST_URL,
            "MISTRAL_API_KEY": local_env["MISTRAL_API_KEY"],
            "AI_TOWN_ENABLE_LLM": "1",
        }

        subprocess.run(
            [sys.executable, "-m", "scripts.migrate"],
            env=env,
            check=True,
        )

        code = r'''
from uuid import uuid4

from app.agents.interactions import run_interactions
from app.db.connection import get_connection
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import initialize_world, record_move
from app.db.snapshots import create_snapshot, verify_replay
from app.llm.budget import get_llm_budget


initialize_world()

for character in ("emma", "noah"):
    result = record_move(
        uuid4(),
        character,
        "square",
        3,
    )
    assert result["accepted"], result

for _ in range(3):
    advance_tick_once(uuid4())


before = get_llm_budget()
assert before["used_requests"] == 0

results = run_interactions(execute=True)

assert len(results) == 1, results
assert results[0].result["accepted"], results

after = get_llm_budget()

assert after["used_requests"] == 1, after

with get_connection() as conn:
    events = conn.execute("""
        SELECT actor, payload
        FROM events
        WHERE type = 'CONVERSATION_SPOKEN'
    """).fetchall()

assert len(events) == 1, events

create_snapshot()
verify_replay()

print("SPEAKER:", events[0][0])
print("LISTENER:", events[0][1]["listener"])
print("DIALOGUE:", events[0][1]["message"])
print("REQUESTS USED:", after["used_requests"])
print("EVENT REPLAY: PASSED")
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
