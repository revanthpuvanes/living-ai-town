from concurrent.futures import ProcessPoolExecutor
from collections import Counter

from app.db.connection import get_connection
from app.db.repository import get_world_state
from app.db.simulation import advance_world_tick
from app.db.snapshots import verify_replay


WORKERS = 8


def advance_once(_):
    return advance_world_tick()


def tick_event_counts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tick_id, COUNT(*)
                FROM events
                WHERE type = 'TICK_ADVANCED'
                GROUP BY tick_id
                ORDER BY tick_id
            """)
            return dict(cur.fetchall())


def tick_rows():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, status
                FROM ticks
                ORDER BY id
            """)
            return dict(cur.fetchall())


def main():
    before = get_world_state()
    start_tick = before["tick"]

    print("=== BEFORE CONCURRENCY ===")
    print("Starting tick:", start_tick)
    print("Workers:", WORKERS)

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(advance_once, range(WORKERS)))

    actual_ticks = [result["tick"] for result in results]
    expected_ticks = list(
        range(start_tick + 1, start_tick + WORKERS + 1)
    )

    print("\n=== WORKER RESULTS ===")
    for result in sorted(results, key=lambda r: r["tick"]):
        print(
            f"Tick {result['tick']} "
            f"Event {result['event_id']}"
        )

    assert sorted(actual_ticks) == expected_ticks, (
        f"Unexpected ticks: {actual_ticks}"
    )
    assert len(set(actual_ticks)) == WORKERS
    assert len(set(r["event_id"] for r in results)) == WORKERS

    after = get_world_state()
    assert after["tick"] == start_tick + WORKERS

    counts = tick_event_counts()
    rows = tick_rows()

    for tick in expected_ticks:
        assert counts.get(tick) == 1, (
            f"Tick {tick} has {counts.get(tick, 0)} events"
        )
        assert rows.get(tick) == "completed", (
            f"Tick {tick} is not completed"
        )

    print("\n=== DATABASE INTEGRITY ===")
    print("Final tick:", after["tick"])
    print("Unique tick events:", WORKERS)
    print("Duplicate tick events: 0")
    print("All new ticks completed: YES")

    print("\n=== REPLAY FIDELITY ===")
    replay = verify_replay()
    assert (
        replay["full_hash"]
        == replay["snapshot_hash"]
        == replay["live_hash"]
    )

    print("Live hash:", replay["live_hash"])
    print("Full replay matches: YES")
    print("Snapshot replay matches: YES")

    print("\nCONCURRENT TICK PROCESSING: PASSED")


if __name__ == "__main__":
    main()
