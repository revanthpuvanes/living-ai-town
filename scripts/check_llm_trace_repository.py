import os
import subprocess
import sys
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)

DB_NAME = f"ai_town_trace_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{DB_NAME}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {DB_NAME}")

    try:
        with psycopg.connect(TEST_URL) as conn:
            conn.execute(open("db/init/001_schema.sql").read())

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
from app.db.llm_traces import (
    get_llm_trace,
    record_llm_trace,
    link_llm_trace_event,
)
from app.llm.client import DialogueGeneration
from app.llm.dialogue import DialogueResponse

with get_connection() as conn:
    conn.execute("""
        INSERT INTO ticks (
            id, status, completed_at, state_hash
        )
        VALUES (0, 'completed', NOW(), %s)
    """, ("0" * 64,))

action_id = uuid4()

generation = DialogueGeneration(
    response=DialogueResponse(
        message="Hello Noah!",
        emotion="friendly",
    ),
    source="mistral",
    model="mistral-small-test",
    prompt_tokens=80,
    completion_tokens=25,
    total_tokens=105,
    latency_ms=420.5,
)

trace = record_llm_trace(
    action_id=action_id,
    tick_id=0,
    speaker="emma",
    listener="noah",
    generation=generation,
)

assert trace.source == "mistral"
assert trace.model == "mistral-small-test"
assert trace.total_tokens == 105
assert trace.event_id is None

duplicate = record_llm_trace(
    action_id=action_id,
    tick_id=0,
    speaker="emma",
    listener="noah",
    generation=generation,
)

assert duplicate.id == trace.id

event_action = uuid4()

with get_connection() as conn:
    event_id = conn.execute("""
        INSERT INTO events (
            action_id,
            tick_id,
            actor,
            type,
            payload,
            rules_version
        )
        VALUES (
            %s, 0, 'emma',
            'CONVERSATION_SPOKEN',
            %s, 1
        )
        RETURNING id
    """, (
        event_action,
        '{"listener": "noah", "message": "Hello Noah!"}',
    )).fetchone()[0]

linked = link_llm_trace_event(action_id, event_id)

assert linked.event_id == event_id
assert get_llm_trace(action_id).event_id == event_id

with get_connection() as conn:
    count = conn.execute(
        "SELECT COUNT(*) FROM llm_traces"
    ).fetchone()[0]

assert count == 1

print("TRACE INSERT: PASSED")
print("TRACE IDEMPOTENCY: PASSED")
print("EVENT LINKING: PASSED")
print("PERSISTENT LLM TRACING: PASSED")
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
            """, (DB_NAME,))

            conn.execute(f"DROP DATABASE {DB_NAME}")

        print("Temporary database cleaned up")


if __name__ == "__main__":
    main()
