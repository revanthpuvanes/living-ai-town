from app.db.connection import get_connection
from app.db.repository import get_world_state
from app.db.simulation import advance_world_tick
from app.engine.replay import replay_events
from app.engine.world import state_hash


print("=== ADVANCE THREE TICKS ===")

for _ in range(3):
    result = advance_world_tick()
    print(
        "Tick:",
        result["tick"],
        "Event:",
        result["event_id"],
    )

print("\n=== LOAD RECORDED EVENTS ===")

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, actor, type, payload, rules_version
            FROM events
            ORDER BY id
            """
        )
        rows = cur.fetchall()

events = [
    {
        "id": row[0],
        "actor": row[1],
        "type": row[2],
        "payload": row[3],
        "rules_version": row[4],
    }
    for row in rows
]

print("Recorded events:", len(events))

print("\n=== REPLAY FROM INITIAL STATE ===")

replayed = replay_events(events)
replayed_hash = state_hash(replayed)

live = get_world_state()
live_hash = live["state_hash"]

print("Live tick:", live["tick"])
print("Replay tick:", replayed["tick"])
print("Live hash:", live_hash)
print("Replay hash:", replayed_hash)

assert replayed == live["state"]
assert replayed_hash == live_hash

print("\nREPLAY FIDELITY: PASSED")
