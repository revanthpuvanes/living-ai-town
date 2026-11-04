from contextlib import nullcontext
from dataclasses import dataclass
from itertools import combinations
from uuid import UUID, uuid5

from app.llm.client import generate_dialogue
from app.llm.context import build_dialogue_context

from app.db.conversations import record_conversation
from app.db.connection import get_connection
from app.db.interaction_locks import try_interaction_lock
from app.db.repository import get_world_state


INTERACTION_NAMESPACE = UUID(
    "b34f1f84-9a8c-48a7-bc39-86587e52e21f"
)

AGENT_IDS = ("emma", "noah", "sophia")

DIALOGUE = {
    ("emma", "noah"): "Good morning, Noah! How are your students?",
    ("emma", "sophia"): "Hello Sophia! How is the shop today?",
    ("noah", "sophia"): "Hello Sophia! How is business going?",
}


@dataclass(frozen=True)
class InteractionResult:
    tick: int
    speaker: str
    listener: str
    message: str
    result: dict | None


def find_interactions(state: dict):
    characters = state["characters"]
    interactions = []

    for speaker, listener in combinations(AGENT_IDS, 2):
        first = characters[speaker]
        second = characters[listener]

        if first["movement"] is not None:
            continue

        if second["movement"] is not None:
            continue

        if first["location"] != second["location"]:
            continue

        # Initially, automatic conversations happen only
        # at the public square.
        if first["location"] != "square":
            continue

        interactions.append((
            speaker,
            listener,
            DIALOGUE[(speaker, listener)],
        ))

    return interactions


def already_spoken_today(
    speaker: str,
    listener: str,
    tick: int,
) -> bool:
    day_start = (tick // 24) * 24

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM events
                    WHERE type = 'CONVERSATION_SPOKEN'
                      AND tick_id >= %s
                      AND tick_id <= %s
                      AND (
                          (actor = %s AND payload->>'listener' = %s)
                          OR
                          (actor = %s AND payload->>'listener' = %s)
                      )
                )
            """, (
                day_start,
                tick,
                speaker,
                listener,
                listener,
                speaker,
            ))
            return cur.fetchone()[0]


def run_interactions(*, execute: bool = False):
    world = get_world_state()
    tick = world["tick"]
    results = []

    for speaker, listener, default_message in find_interactions(
        world["state"]
    ):
        day = tick // 24

        lock = (
            try_interaction_lock(speaker, listener, day)
            if execute
            else nullcontext(True)
        )

        with lock as acquired:
            if not acquired:
                continue

            # Recheck under the lock. This prevents duplicate
            # LLM calls from competing scheduler workers.
            if already_spoken_today(speaker, listener, tick):
                continue

            message = default_message

            action_id = uuid5(
                INTERACTION_NAMESPACE,
                f"{tick}:{speaker}:{listener}",
            )

            if execute:
                context = build_dialogue_context(
                    speaker,
                    listener,
                )
                generation = generate_dialogue(context)

                if generation.source == "mistral":
                    message = generation.response.message

                result = record_conversation(
                    action_id,
                    speaker,
                    listener,
                    message,
                    expected_tick=tick,
                    expected_state_hash=world["state_hash"],
                    llm_generation=generation,
                    auto_pair_day=(
                        f"{day}:"
                        + ":".join(sorted((speaker, listener)))
                    ),
                )
            else:
                result = None

            results.append(InteractionResult(
                tick=tick,
                speaker=speaker,
                listener=listener,
                message=message,
                result=result,
            ))

    return results
