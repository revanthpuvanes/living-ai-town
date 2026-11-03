from uuid import UUID, uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.engine.world import advance_tick, state_hash


def advance_tick_once(request_id: UUID):
    """
    Advance exactly one logical tick per request UUID.

    PostgreSQL's world_state row lock serializes workers.
    The request_id unique index provides durable deduplication.
    """

    if not isinstance(request_id, UUID):
        raise TypeError("request_id must be a UUID")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Serialize all tick processing.
            cur.execute("""
                SELECT current_tick, state
                FROM world_state
                WHERE id = 1
                FOR UPDATE
            """)

            row = cur.fetchone()
            if row is None:
                raise RuntimeError("World not initialized")

            current_tick, current_state = row

            # Check whether another worker already completed
            # this logical request.
            cur.execute("""
                SELECT t.id, e.id, t.state_hash
                FROM ticks t
                JOIN events e
                  ON e.tick_id = t.id
                 AND e.type = 'TICK_ADVANCED'
                WHERE t.request_id = %s
                  AND t.status = 'completed'
            """, (request_id,))

            existing = cur.fetchone()

            if existing is not None:
                tick, event_id, digest = existing

                return {
                    "tick": tick,
                    "event_id": event_id,
                    "state_hash": digest.strip(),
                    "duplicate": True,
                }

            next_tick = current_tick + 1
            updated_state = advance_tick(current_state)
            digest = state_hash(updated_state)

            event_action_id = uuid5(
                NAMESPACE_URL,
                f"living-ai-town:tick:{next_tick}",
            )

            cur.execute("""
                INSERT INTO ticks (
                    id, status, request_id
                )
                VALUES (%s, 'running', %s)
            """, (next_tick, request_id))

            cur.execute("""
                INSERT INTO events (
                    action_id,
                    tick_id,
                    actor,
                    type,
                    payload,
                    rules_version
                )
                VALUES (
                    %s, %s, 'system',
                    'TICK_ADVANCED', %s, 1
                )
                RETURNING id
            """, (
                event_action_id,
                next_tick,
                Jsonb({"tick": next_tick}),
            ))

            event_id = cur.fetchone()[0]

            cur.execute("""
                UPDATE world_state
                SET current_tick = %s,
                    state = %s,
                    state_hash = %s,
                    last_event_id = %s
                WHERE id = 1
            """, (
                next_tick,
                Jsonb(updated_state),
                digest,
                event_id,
            ))

            cur.execute("""
                UPDATE ticks
                SET status = 'completed',
                    completed_at = NOW(),
                    state_hash = %s
                WHERE id = %s
            """, (digest, next_tick))

            return {
                "tick": next_tick,
                "event_id": event_id,
                "state_hash": digest,
                "duplicate": False,
            }
