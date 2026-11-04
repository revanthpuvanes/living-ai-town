import os
import subprocess
import sys
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)

TEST_DB = f"ai_town_llm_{uuid4().hex[:12]}"

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
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

from app.agents.interactions import run_interactions
from app.db.connection import get_connection
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import initialize_world, record_move
from app.db.snapshots import create_snapshot, verify_replay
from app.llm.client import DialogueGeneration
from app.llm.dialogue import DialogueResponse


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


generation_started = threading.Event()
generation_count = 0
count_lock = threading.Lock()


def fake_generate(context):
    global generation_count

    with count_lock:
        generation_count += 1

    generation_started.set()

    # Keep the first worker's advisory lock occupied
    # while the second worker attempts the interaction.
    time.sleep(0.5)

    return DialogueGeneration(
        response=DialogueResponse(
            message="How are your students today?",
            emotion="curious",
        ),
        source="mistral",
    )


def first_worker():
    return run_interactions(execute=True)


def second_worker():
    assert generation_started.wait(timeout=5)
    return run_interactions(execute=True)


with patch(
    "app.agents.interactions.generate_dialogue",
    side_effect=fake_generate,
):
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_worker)
        second = pool.submit(second_worker)

        first_results = first.result(timeout=15)
        second_results = second.result(timeout=15)


assert generation_count == 1, generation_count

all_results = first_results + second_results

assert len(all_results) == 1, all_results
assert all_results[0].result["accepted"]
assert not all_results[0].result["duplicate"]

with get_connection() as conn:
    events = conn.execute("""
        SELECT actor, payload
        FROM events
        WHERE type = 'CONVERSATION_SPOKEN'
    """).fetchall()

assert len(events) == 1, events
assert events[0][0] == "emma"
assert events[0][1]["listener"] == "noah"
assert events[0][1]["message"] == (
    "How are your students today?"
)

create_snapshot()
verify_replay()

print("DIALOGUE GENERATIONS:", generation_count)
print("PERSISTED CONVERSATIONS:", len(events))
print("CONCURRENT INTERACTIONS: PASSED")
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
