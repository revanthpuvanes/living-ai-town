"""Persist validated visitor messages in the append-only event log."""

from uuid import uuid4

from psycopg.types.json import Jsonb

from app.db.connection import get_connection


def record_visitor_message(character_id: str, message: str):
    if character_id not in ("emma", "noah", "sophia"):
        raise ValueError("Unknown character")

    if not isinstance(message, str):
        raise ValueError("Message must be text")

    message = message.strip()

    if not message or len(message) > 300:
        raise ValueError("Message must contain 1–300 characters")

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

            if character_id not in state["characters"]:
                raise ValueError("Character not found in world")

            cur.execute("""
                INSERT INTO events (
                    action_id, tick_id, actor,
                    type, payload, rules_version
                )
                VALUES (
                    %s, %s, 'visitor',
                    'VISITOR_MESSAGE', %s, %s
                )
                RETURNING id
            """, (
                uuid4(),
                tick,
                Jsonb({
                    "tick": tick,
                    "character_id": character_id,
                    "message": message,
                }),
                state["rules_version"],
            ))

            event_id = cur.fetchone()[0]

            cur.execute("""
                UPDATE world_state
                SET last_event_id = %s
                WHERE id = 1
            """, (event_id,))

            return {
                "accepted": True,
                "event_id": event_id,
                "tick": tick,
                "character_id": character_id,
                "message": message,
            }
