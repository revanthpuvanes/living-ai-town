import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.db.connection import get_connection
from app.db.repository import get_world_state
from app.db.simulation import advance_world_tick
from app.db.snapshots import verify_replay


def counts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            events = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ticks")
            ticks = cur.fetchone()[0]
    return events, ticks


before = get_world_state()
before_counts = counts()
next_tick = before["tick"] + 1

print("=== BEFORE PROCESS CRASH ===")
print("Current tick:", before["tick"])
print("Database counts:", before_counts)

worker_code = """
import sys
import time
from uuid import uuid4
from psycopg.types.json import Jsonb
from app.db.connection import get_connection

tick = int(sys.argv[1])
ready_file = sys.argv[2]

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT id FROM world_state WHERE id=1 FOR UPDATE'
        )
        cur.execute(
            "INSERT INTO ticks (id, status) VALUES (%s, 'running')",
            (tick,),
        )
        cur.execute(
            '''
            INSERT INTO events (
                action_id, tick_id, actor,
                type, payload, rules_version
            )
            VALUES (%s, %s, 'system', 'TICK_ADVANCED', %s, 1)
            ''',
            (uuid4(), tick, Jsonb({"tick": tick})),
        )

        # Transaction is still uncommitted.
        with open(ready_file, "w") as f:
            f.write("ready")

        time.sleep(60)
"""

with tempfile.TemporaryDirectory() as temp:
    ready = Path(temp) / "ready"

    worker = subprocess.Popen(
        [
            sys.executable,
            "-c",
            worker_code,
            str(next_tick),
            str(ready),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        deadline = time.monotonic() + 10

        while not ready.exists():
            if worker.poll() is not None:
                error = worker.stderr.read().decode()
                raise RuntimeError(f"Worker failed: {error}")
            if time.monotonic() > deadline:
                raise TimeoutError("Worker did not become ready")
            time.sleep(0.05)

        print("\n=== KILLING WORKER MID-TRANSACTION ===")
        os.kill(worker.pid, signal.SIGKILL)
        worker.wait(timeout=5)
        print("Worker exit code:", worker.returncode)
        assert worker.returncode == -signal.SIGKILL

    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()

print("\n=== VERIFY CRASH ROLLBACK ===")
after = get_world_state()
after_counts = counts()

assert after == before
assert after_counts == before_counts

print("World unchanged: YES")
print("Database counts:", after_counts)
print("PROCESS CRASH ROLLBACK: PASSED")

print("\n=== RESTART TICK PROCESSING ===")
result = advance_world_tick()
assert result["tick"] == next_tick
print("Recovered tick:", result["tick"])

print("\n=== VERIFY REPLAY ===")
replay = verify_replay()
assert replay["live_hash"] == replay["full_hash"]
assert replay["live_hash"] == replay["snapshot_hash"]

print("REPLAY AFTER RECOVERY: PASSED")
print("State hash:", replay["live_hash"])

print("\n=== VERIFY NO DUPLICATE TICK ===")
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM ticks WHERE id = %s",
            (next_tick,),
        )
        assert cur.fetchone()[0] == 1

        cur.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE tick_id = %s AND type = 'TICK_ADVANCED'
            """,
            (next_tick,),
        )
        assert cur.fetchone()[0] == 1

print("Exactly one completed tick and event: YES")
print("\nPROCESS CRASH RECOVERY: PASSED")
