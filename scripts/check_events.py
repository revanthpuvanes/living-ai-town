from uuid import UUID

from app.db.repository import (
    initialize_world,
    get_world_state,
    record_move,
)

print("=== INITIALIZE WORLD ===")
world = initialize_world()
print("Tick:", world["tick"])
print("Initial hash:", world["state_hash"])

print("\n=== ACCEPT MOVEMENT ===")
action_id = UUID("11111111-1111-4111-8111-111111111111")

first = record_move(
    action_id,
    "emma",
    "square",
    3,
)
print(first)

assert first["accepted"] is True

print("\n=== REPEAT SAME ACTION ===")
second = record_move(
    action_id,
    "emma",
    "square",
    3,
)
print(second)

assert second["duplicate"] is True
assert second["event_id"] == first["event_id"]

print("\n=== REJECT INVALID ACTION ===")
before = get_world_state()

rejected = record_move(
    UUID("22222222-2222-4222-8222-222222222222"),
    "emma",
    "unknown_location",
    3,
)
print(rejected)

after = get_world_state()

assert rejected["accepted"] is False
assert before["state_hash"] == after["state_hash"]

print("\n=== DATABASE EVENT CHECK ===")
from app.db.connection import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM events")
        print("Accepted events:", cur.fetchone()[0])

        cur.execute(
            "SELECT COUNT(*) FROM decisions "
            "WHERE validator_result LIKE 'rejected:%'"
        )
        print("Rejected decisions:", cur.fetchone()[0])

print("\nALL CHECKS PASSED")
