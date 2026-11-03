from uuid import uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.engine.world import advance_tick, state_hash


def advance_world_tick():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT current_tick, state
                FROM world_state
                WHERE id = 1
                FOR UPDATE
                """
            )
            row = cur.fetchone()

            if row is None:
                raise RuntimeError("World not initialized")

            current_tick, state = row
            next_tick = current_tick + 1

            action_id = uuid5(
                NAMESPACE_URL,
                f"living-ai-town:tick:{next_tick}",
            )

            cur.execute(
                "SELECT id FROM events WHERE action_id = %s",
                (action_id,),
            )
            if cur.fetchone():
                raise RuntimeError(
                    "Tick event already exists but state is behind"
                )

            updated = advance_tick(state)
            digest = state_hash(updated)

            cur.execute(
                """
                INSERT INTO ticks (id, status)
                VALUES (%s, 'running')
                """,
                (next_tick,),
            )

            cur.execute(
                """
                INSERT INTO events (
                    action_id, tick_id, actor,
                    type, payload, rules_version
                )
                VALUES (%s, %s, 'system',
                        'TICK_ADVANCED', %s, 1)
                RETURNING id
                """,
                (
                    action_id,
                    next_tick,
                    Jsonb({"tick": next_tick}),
                ),
            )
            event_id = cur.fetchone()[0]

            cur.execute(
                """
                UPDATE world_state
                SET current_tick = %s,
                    state = %s,
                    state_hash = %s,
                    last_event_id = %s
                WHERE id = 1
                """,
                (
                    next_tick,
                    Jsonb(updated),
                    digest,
                    event_id,
                ),
            )

            cur.execute(
                """
                UPDATE ticks
                SET status = 'completed',
                    completed_at = now(),
                    state_hash = %s
                WHERE id = %s
                """,
                (digest, next_tick),
            )

            return {
                "tick": next_tick,
                "event_id": event_id,
                "state_hash": digest,
            }
