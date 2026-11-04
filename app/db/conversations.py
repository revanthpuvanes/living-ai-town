from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.db.llm_traces import record_llm_trace
from app.engine.conversations import validate_conversation
from app.engine.world import InvalidAction, RULES_VERSION


def record_conversation(
    action_id: UUID,
    speaker_id: str,
    listener_id: str,
    message: str,
    *,
    expected_tick: int | None = None,
    expected_state_hash: str | None = None,
    auto_pair_day: str | None = None,
    llm_generation=None,
):
    action_id = UUID(str(action_id))

    proposed_action = {
        "action": "speak",
        "speaker": speaker_id,
        "listener": listener_id,
        "message": message,
    }

    if auto_pair_day is not None:
        proposed_action["auto_pair_day"] = auto_pair_day

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_tick, state, state_hash
                FROM world_state
                WHERE id = 1
                FOR UPDATE
            """)
            row = cur.fetchone()

            if row is None:
                raise RuntimeError("World not initialized")

            tick, state, current_hash = row

            cur.execute("""
                SELECT d.raw_output, d.validator_result, e.id
                FROM decisions d
                LEFT JOIN events e ON e.action_id = d.action_id
                WHERE d.action_id = %s
            """, (action_id,))
            previous = cur.fetchone()

            if previous is not None:
                old_action, old_result, event_id = previous

                if old_action != proposed_action:
                    raise InvalidAction(
                        "Action ID reused with different payload"
                    )

                if old_result == "accepted":
                    if event_id is None:
                        raise RuntimeError(
                            "Accepted conversation missing event"
                        )
                    return {
                        "accepted": True,
                        "duplicate": True,
                        "event_id": event_id,
                    }

                return {
                    "accepted": False,
                    "duplicate": True,
                    "reason": old_result.removeprefix("rejected: "),
                }

            # Protect against IDs used by another event type.
            cur.execute("""
                SELECT id FROM events WHERE action_id = %s
            """, (action_id,))
            if cur.fetchone() is not None:
                raise InvalidAction("Action ID already used")

            if expected_tick is not None and tick != expected_tick:
                raise InvalidAction(
                    "Stale observation: world tick changed"
                )

            if (
                expected_state_hash is not None
                and current_hash.strip() != expected_state_hash
            ):
                raise InvalidAction(
                    "Stale observation: world state changed"
                )

            try:
                validate_conversation(
                    state, speaker_id, listener_id, message
                )
            except InvalidAction as exc:
                cur.execute("""
                    INSERT INTO decisions (
                        id, action_id, tick_id, agent,
                        raw_output, validator_result
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    uuid4(),
                    action_id,
                    tick,
                    speaker_id,
                    Jsonb(proposed_action),
                    f"rejected: {exc}",
                ))
                return {
                    "accepted": False,
                    "duplicate": False,
                    "reason": str(exc),
                }

            if auto_pair_day is not None:
                expected_key = (
                    f"{tick // 24}:"
                    + ":".join(sorted((speaker_id, listener_id)))
                )
                if auto_pair_day != expected_key:
                    raise InvalidAction(
                        "Invalid automatic conversation pair/day key"
                    )

                # The world_state row lock serializes conversation
                # transactions, including concurrent scheduler workers.
                cur.execute("""
                    SELECT id
                    FROM events
                    WHERE type = 'CONVERSATION_SPOKEN'
                      AND payload->>'auto_pair_day' = %s
                    LIMIT 1
                """, (auto_pair_day,))
                previous_pair = cur.fetchone()

                if previous_pair is not None:
                    return {
                        "accepted": True,
                        "duplicate": True,
                        "event_id": previous_pair[0],
                    }

            location = state["characters"][speaker_id]["location"]

            cur.execute("""
                INSERT INTO decisions (
                    id, action_id, tick_id, agent,
                    raw_output, validator_result
                )
                VALUES (%s, %s, %s, %s, %s, 'accepted')
            """, (
                uuid4(),
                action_id,
                tick,
                speaker_id,
                Jsonb(proposed_action),
            ))

            cur.execute("""
                INSERT INTO events (
                    action_id, tick_id, actor,
                    type, payload, rules_version
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                action_id,
                tick,
                speaker_id,
                "CONVERSATION_SPOKEN",
                Jsonb({
                    "listener": listener_id,
                    "message": message,
                    "tick": tick,
                    "location": location,
                    **(
                        {"auto_pair_day": auto_pair_day}
                        if auto_pair_day is not None
                        else {}
                    ),
                }),
                RULES_VERSION,
            ))

            event_id = cur.fetchone()[0]

            if llm_generation is not None:
                record_llm_trace(
                    action_id=action_id,
                    event_id=event_id,
                    tick_id=tick,
                    speaker=speaker_id,
                    listener=listener_id,
                    generation=llm_generation,
                    conn=conn,
                )

            cur.execute("""
                UPDATE world_state
                SET last_event_id = %s
                WHERE id = 1
            """, (event_id,))

            return {
                "accepted": True,
                "duplicate": False,
                "event_id": event_id,
                "tick": tick,
                "location": location,
            }


def get_recent_conversations(character_id: str, limit: int = 20):
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, tick_id, actor, payload
                FROM events
                WHERE type = 'CONVERSATION_SPOKEN'
                  AND (
                      actor = %s
                      OR payload->>'listener' = %s
                  )
                ORDER BY id DESC
                LIMIT %s
            """, (character_id, character_id, limit))

            rows = cur.fetchall()

    return [
        {
            "event_id": row[0],
            "tick": row[1],
            "speaker": row[2],
            "listener": row[3]["listener"],
            "message": row[3]["message"],
            "location": row[3]["location"],
        }
        for row in rows
    ]
