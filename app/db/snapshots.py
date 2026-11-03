from app.db.connection import get_connection
from app.engine.replay import apply_event, replay_events
from app.engine.world import RULES_VERSION, state_hash
from psycopg.types.json import Jsonb


def create_snapshot():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_tick, rules_version, state,
                       state_hash, last_event_id
                FROM world_state
                WHERE id = 1
                FOR UPDATE
            """)
            row = cur.fetchone()

            if row is None:
                raise RuntimeError("World not initialized")

            tick, version, state, digest, event_id = row

            if version != RULES_VERSION:
                raise ValueError("Incompatible rules version")

            if state_hash(state) != digest.strip():
                raise ValueError("Live state hash mismatch")

            cur.execute("""
                INSERT INTO snapshots (
                    tick_id, last_event_id, rules_version,
                    state, state_hash
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tick_id) DO NOTHING
                RETURNING id
            """, (
                tick, event_id, version,
                Jsonb(state), digest,
            ))

            result = cur.fetchone()
            return {
                "tick": tick,
                "created": result is not None,
                "state_hash": digest.strip(),
            }


def verify_replay():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tick_id, last_event_id,
                       rules_version, state, state_hash
                FROM snapshots
                ORDER BY tick_id DESC
                LIMIT 1
            """)
            snapshot = cur.fetchone()

            if snapshot is None:
                raise RuntimeError("No snapshot available")

            tick, last_id, version, saved_state, saved_hash = snapshot

            if version != RULES_VERSION:
                raise ValueError("Snapshot rules version mismatch")

            if state_hash(saved_state) != saved_hash.strip():
                raise ValueError("Corrupted snapshot")

            cur.execute("""
                SELECT id, actor, type, payload, rules_version
                FROM events
                ORDER BY id
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT state, state_hash
                FROM world_state
                WHERE id = 1
            """)
            live_state, live_hash = cur.fetchone()

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

    # Replay from the original initial state.
    full_state = replay_events(events)

    # Replay only events after the snapshot boundary.
    snapshot_state = saved_state
    for event in events:
        if last_id is None or event["id"] > last_id:
            snapshot_state = apply_event(snapshot_state, event)

    full_hash = state_hash(full_state)
    snapshot_hash = state_hash(snapshot_state)

    if not (
        full_hash == snapshot_hash == live_hash.strip()
        and full_state == snapshot_state == live_state
    ):
        raise AssertionError("Replay fidelity mismatch")

    return {
        "snapshot_tick": tick,
        "total_events": len(events),
        "events_after_snapshot": sum(
            1 for event in events
            if last_id is None or event["id"] > last_id
        ),
        "full_hash": full_hash,
        "snapshot_hash": snapshot_hash,
        "live_hash": live_hash.strip(),
    }
