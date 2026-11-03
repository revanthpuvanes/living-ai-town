from uuid import UUID, uuid4

from app.db.connection import get_connection
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay

ORIGINAL_REQUEST = UUID(
    "386a2b70-68e0-4abe-b0e5-4c74156cdd1f"
)


def event_count():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            return cur.fetchone()[0]


print("=== VERIFY PERSISTED STATE ===")
before = get_world_state()
assert before["tick"] == 15, before
assert before["state_hash"] == (
    "75d575c83777f3b8a94820f527a53ba325ff37e523a0c0b787be418eba3fdc63"
)
print("Tick 15 persisted: YES")

print("\n=== RETRY ORIGINAL REQUEST ===")
count_before = event_count()
original = advance_tick_once(ORIGINAL_REQUEST)

assert original["tick"] == 15
assert original["event_id"] == 26
assert original["duplicate"] is True
assert event_count() == count_before
assert get_world_state() == before

print("Original event recovered:", original["event_id"])
print("Duplicate event created: NO")

print("\n=== ADVANCE NEW REQUEST ===")
new_result = advance_tick_once(uuid4())
assert new_result["tick"] == 16
assert new_result["duplicate"] is False
assert event_count() == count_before + 1

print("New tick:", new_result["tick"])

print("\n=== VERIFY REPLAY ===")
replay = verify_replay()
assert replay["full_hash"] == replay["snapshot_hash"] == replay["live_hash"]

print("Replay hash:", replay["live_hash"])
print("\nDATABASE RESTART RECOVERY: PASSED")
