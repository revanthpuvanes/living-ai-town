from uuid import UUID, uuid5

from app.db.connection import get_connection
from app.db.conversations import record_conversation
from app.db.interaction_locks import try_interaction_lock
from app.db.repository import get_world_state
from app.llm.client import generate_dialogue
from app.llm.context import build_dialogue_context


REPLY_NAMESPACE = UUID(
    "e3171a8b-11df-49a9-a52d-289de2bd07a4"
)


def reply_exists(opening_event_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM events
                    WHERE type = 'CONVERSATION_SPOKEN'
                      AND payload->>'reply_to_event_id' = %s
                )
            """, (str(opening_event_id),))
            return cur.fetchone()[0]


def process_reply(opening, *, lock_held=False):
    """Generate and record one reply to an automatic conversation."""
    from contextlib import nullcontext

    day = opening["tick"] // 24
    speaker = opening["listener"]
    listener = opening["speaker"]

    lock = (
        nullcontext(True)
        if lock_held
        else try_interaction_lock(speaker, listener, day)
    )

    with lock as acquired:
        if not acquired:
            return None

        if reply_exists(opening["event_id"]):
            return None

        world = get_world_state()
        tick = world["tick"]
        state = world["state"]

        first = state["characters"][speaker]
        second = state["characters"][listener]

        if first["movement"] is not None:
            return None

        if second["movement"] is not None:
            return None

        if first["location"] != second["location"]:
            return None

        if first["location"] != opening["location"]:
            return None

        context = build_dialogue_context(speaker, listener)

        generation = generate_dialogue(
            context,
            reply_to=opening["message"],
        )

        message = generation.response.message

        action_id = uuid5(
            REPLY_NAMESPACE,
            f"reply:{opening['event_id']}",
        )

        return record_conversation(
            action_id,
            speaker,
            listener,
            message,
            expected_tick=tick,
            expected_state_hash=world["state_hash"],
            reply_to_event_id=opening["event_id"],
            llm_generation=generation,
        )
