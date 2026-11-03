from concurrent.futures import ProcessPoolExecutor
from uuid import uuid4

from app.db.connection import get_connection
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay


WORKERS = 8


def run_worker(request_id):
    return advance_tick_once(request_id)


def event_count():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            return cur.fetchone()[0]


def main():
    request_id = uuid4()

    before = get_world_state()
    before_events = event_count()

    print("=== SAME LOGICAL TICK TEST ===")
    print("Starting tick:", before["tick"])
    print("Workers:", WORKERS)
    print("Shared request ID:", request_id)

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        results = list(
            pool.map(
                run_worker,
                [request_id] * WORKERS,
            )
        )

    print("\n=== WORKER RESULTS ===")
    for index, result in enumerate(results, start=1):
        print(
            f"Worker {index}: "
            f"tick={result['tick']} "
            f"event={result['event_id']} "
            f"duplicate={result['duplicate']}"
        )

    after = get_world_state()
    after_events = event_count()

    assert after["tick"] == before["tick"] + 1
    assert after_events == before_events + 1

    assert len(set(r["tick"] for r in results)) == 1
    assert len(set(r["event_id"] for r in results)) == 1

    assert sum(not r["duplicate"] for r in results) == 1
    assert sum(r["duplicate"] for r in results) == WORKERS - 1

    print("\n=== DATABASE INTEGRITY ===")
    print("New ticks:", after["tick"] - before["tick"])
    print("New events:", after_events - before_events)
    print("Original executions:", 1)
    print("Deduplicated retries:", WORKERS - 1)

    print("\n=== REPLAY INTEGRITY ===")
    replay = verify_replay()

    assert (
        replay["full_hash"]
        == replay["snapshot_hash"]
        == replay["live_hash"]
    )

    print("Full replay matches: YES")
    print("Snapshot replay matches: YES")

    print("\nSAME-TICK IDEMPOTENCY: PASSED")


if __name__ == "__main__":
    main()
