from uuid import UUID, uuid4

from app.db.connection import get_connection
from app.db.repository import get_world_state, record_move
from app.engine.world import InvalidAction

accepted_id = UUID("11111111-1111-4111-8111-111111111111")
rejected_id = UUID("22222222-2222-4222-8222-222222222222")


def counts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            events = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM decisions")
            decisions = cur.fetchone()[0]
    return events, decisions


before_state = get_world_state()
before_counts = counts()

print("=== ACCEPTED ACTION RETRY ===")
result = record_move(accepted_id, "emma", "square", 3)
assert result["accepted"] and result["duplicate"]
print("Same payload: accepted as duplicate")

print("\n=== ACCEPTED ACTION PAYLOAD CONFLICT ===")
try:
    record_move(accepted_id, "emma", "shop", 3)
    raise AssertionError("Conflicting payload was accepted")
except InvalidAction as exc:
    print("Conflict blocked:", exc)

print("\n=== REJECTED ACTION RETRY ===")
result = record_move(rejected_id, "emma", "unknown_location", 3)
assert not result["accepted"] and result["duplicate"]
print("Same rejected payload: duplicate detected")

print("\n=== REJECTED ACTION PAYLOAD CONFLICT ===")
try:
    record_move(rejected_id, "emma", "bakery", 3)
    raise AssertionError("Conflicting payload was accepted")
except InvalidAction as exc:
    print("Conflict blocked:", exc)

print("\n=== NEW REJECTED ACTION IDEMPOTENCY ===")
new_id = uuid4()
first = record_move(new_id, "noah", "invalid_location", 2)
second = record_move(new_id, "noah", "invalid_location", 2)

assert not first["accepted"] and not first["duplicate"]
assert not second["accepted"] and second["duplicate"]
print("New rejection recorded once; retry detected")

after_state = get_world_state()
after_counts = counts()

assert before_state == after_state
assert after_counts[0] == before_counts[0]
assert after_counts[1] == before_counts[1] + 1

print("\nWorld state unchanged: YES")
print("Accepted events unchanged: YES")
print("Only one new rejected decision: YES")
print("\nPAYLOAD IDEMPOTENCY: PASSED")
