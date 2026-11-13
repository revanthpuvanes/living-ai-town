"""Generate deterministic, traceable replies to visitor messages."""

from uuid import uuid4

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.llm.client import generate_visitor_reply


REPLIES = {
    "emma": "Welcome to my bakery! Thanks for stopping by.",
    "noah": "Hello! It's always nice to meet someone new in town.",
    "sophia": "Welcome! Feel free to look around my shop.",
}


def reply_to_pending_visitors(limit=5):
    if not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Invalid reply limit")

    results = []

    # Fetch pending messages and recent context without holding
    # the world-state row lock during Mistral requests.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.payload
                FROM events AS m
                WHERE m.type = 'VISITOR_MESSAGE'
                  AND NOT EXISTS (
                      SELECT 1 FROM events AS r
                      WHERE r.type = 'VISITOR_REPLY'
                        AND m.id = ANY(r.depends_on)
                  )
                ORDER BY m.id
                LIMIT %s
            """, (limit,))
            pending = cur.fetchall()

            cur.execute("""
                SELECT actor, type, payload
                FROM events
                WHERE type IN (
                    'CONVERSATION_SPOKEN',
                    'MOVE_STARTED',
                    'VISITOR_REPLY'
                )
                ORDER BY id DESC
                LIMIT 8
            """)
            recent_events = [
                {
                    "actor": actor,
                    "type": event_type,
                    "payload": payload,
                }
                for actor, event_type, payload in cur.fetchall()
            ]

    # Generate replies outside the database transaction.
    generated = []
    for message_id, payload in pending:
        character_id = payload["character_id"]

        reply = generate_visitor_reply(
            character_id,
            payload["message"],
            recent_events,
        )
        generated.append((message_id, character_id, reply))

    # Record replies atomically and preserve event dependencies.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_tick, state
                FROM world_state
                WHERE id = 1
                FOR UPDATE
            """)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("World not initialized")

            tick, state = row

            for message_id, character_id, reply in generated:
                if character_id not in state["characters"]:
                    raise ValueError("Unknown visitor recipient")

                # Recheck: another worker may already have replied.
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM events
                        WHERE type = 'VISITOR_REPLY'
                          AND %s = ANY(depends_on)
                    )
                """, (message_id,))

                if cur.fetchone()[0]:
                    continue

                cur.execute("""
                    INSERT INTO events (
                        action_id, tick_id, actor, type,
                        payload, depends_on, rules_version
                    )
                    VALUES (
                        %s, %s, %s, 'VISITOR_REPLY',
                        %s, %s, %s
                    )
                    RETURNING id
                """, (
                    uuid4(),
                    tick,
                    character_id,
                    Jsonb({
                        "tick": tick,
                        "message": reply,
                        "visitor_event_id": message_id,
                    }),
                    [message_id],
                    state["rules_version"],
                ))

                reply_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO event_context (event_id, seen_event_id)
                    VALUES (%s, %s)
                """, (reply_id, message_id))

                results.append({
                    "event_id": reply_id,
                    "depends_on": message_id,
                    "character_id": character_id,
                    "message": reply,
                })

            if results:
                cur.execute("""
                    UPDATE world_state
                    SET last_event_id = %s
                    WHERE id = 1
                """, (results[-1]["event_id"],))

    return results
