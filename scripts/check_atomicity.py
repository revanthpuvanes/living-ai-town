from uuid import uuid4

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.db.repository import get_world_state
from app.engine.world import advance_tick, state_hash


class SimulatedCrash(Exception):
    pass


def database_counts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            events = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ticks")
            ticks = cur.fetchone()[0]

            return events, ticks


print("=== BEFORE FAILURE ===")
before = get_world_state()
counts_before = database_counts()

print("Tick:", before["tick"])
print("State hash:", before["state_hash"])
print("Events, ticks:", counts_before)

print("\n=== INJECT FAILURE INSIDE TRANSACTION ===")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_tick, state
                FROM world_state
                WHERE id = 1
                FOR UPDATE
            """)
            current_tick, state = cur.fetchone()

            next_tick = current_tick + 1
            updated = advance_tick(state)
            digest = state_hash(updated)

            cur.execute("""
                INSERT INTO ticks (id, status)
                VALUES (%s, 'running')
            """, (next_tick,))

            cur.execute("""
                INSERT INTO events (
                    action_id, tick_id, actor,
                    type, payload, rules_version
                )
                VALUES (%s, %s, 'system',
                        'TICK_ADVANCED', %s, 1)
            """, (
                uuid4(),
                next_tick,
                Jsonb({"tick": next_tick}),
            ))

            # Deliberately fail after the event insert
            # but before updating world_state.
            raise SimulatedCrash(
                "Injected failure before state projection update"
            )

except SimulatedCrash as exc:
    print("Caught expected failure:", exc)

print("\n=== AFTER FAILURE ===")
after = get_world_state()
counts_after = database_counts()

print("Tick:", after["tick"])
print("State hash:", after["state_hash"])
print("Events, ticks:", counts_after)

assert after == before, "World state changed after rollback"
assert counts_after == counts_before, "Partial database commit detected"

print("\nATOMICITY ROLLBACK: PASSED")
