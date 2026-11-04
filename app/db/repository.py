from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.engine.world import (
    InvalidAction,
    initial_state,
    start_move,
    state_hash,
)


def initialize_world():
    state = initial_state()
    digest = state_hash(state)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ticks
                    (id, status, completed_at, state_hash)
                VALUES (0, 'completed', now(), %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (digest,),
            )

            cur.execute(
                """
                INSERT INTO world_state
                    (id, current_tick, rules_version, state, state_hash)
                VALUES (1, 0, 1, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (Jsonb(state), digest),
            )

    return get_world_state()


def get_world_state():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT current_tick, state, state_hash
                FROM world_state
                WHERE id = 1
                """
            )
            row = cur.fetchone()

    if row is None:
        raise RuntimeError("World has not been initialized")

    return {
        "tick": row[0],
        "state": row[1],
        "state_hash": row[2].strip(),
    }


def record_move(
    action_id: UUID,
    character_id: str,
    destination: str,
    duration_ticks: int,
    *,
    expected_tick: int | None = None,
    expected_state_hash: str | None = None,
):
    action_id = UUID(str(action_id))

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Serialize requests through the world row lock.
            cur.execute(
                """
                SELECT current_tick, state, state_hash
                FROM world_state
                WHERE id = 1
                FOR UPDATE
                """
            )
            row = cur.fetchone()

            if row is None:
                raise RuntimeError("World has not been initialized")

            current_tick, state, current_hash = row

            proposed_action = {
                "action": "move",
                "character_id": character_id,
                "destination": destination,
                "duration_ticks": duration_ticks,
            }

            # Check both accepted and rejected action IDs.
            cur.execute(
                "SELECT id FROM events WHERE action_id = %s",
                (action_id,),
            )
            existing = cur.fetchone()

            if existing:
                cur.execute(
                    """
                    SELECT raw_output
                    FROM decisions
                    WHERE action_id = %s
                      AND validator_result = 'accepted'
                    """,
                    (action_id,),
                )
                previous = cur.fetchone()

                if previous is None:
                    # Legacy event: created before decisions.action_id
                    # existed. Validate against the immutable event.
                    cur.execute(
                        """
                        SELECT actor, payload
                        FROM events
                        WHERE action_id = %s
                          AND type = 'MOVE_STARTED'
                        """,
                        (action_id,),
                    )
                    legacy = cur.fetchone()

                    if legacy is None:
                        raise InvalidAction(
                            "Action ID has no matching move event"
                        )

                    actor, payload = legacy

                    matches = (
                        actor == character_id
                        and payload.get("to") == destination
                        and payload.get("duration_ticks")
                            == duration_ticks
                    )

                    if not matches:
                        raise InvalidAction(
                            "Action ID reused with different payload"
                        )

                elif previous[0] != proposed_action:
                    raise InvalidAction(
                        "Action ID reused with different payload"
                    )

                return {
                    "accepted": True,
                    "duplicate": True,
                    "event_id": existing[0],
                }

            cur.execute(
                """
                SELECT validator_result, raw_output
                FROM decisions
                WHERE action_id = %s
                """,
                (action_id,),
            )
            previous = cur.fetchone()

            if previous:
                result, previous_action = previous

                if previous_action != proposed_action:
                    raise InvalidAction(
                        "Action ID reused with different payload"
                    )

                return {
                    "accepted": False,
                    "duplicate": True,
                    "reason": result.removeprefix("rejected: "),
                }

            # Existing action IDs are handled above so retries remain
            # idempotent even after the world has advanced.
            if expected_tick is not None and current_tick != expected_tick:
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
                updated = start_move(
                    state,
                    character_id,
                    destination,
                    duration_ticks,
                )
            except InvalidAction as exc:
                # Rejected decisions are recorded.
                # No authoritative state is modified.
                cur.execute(
                    """
                    INSERT INTO decisions (
                        id, action_id, tick_id, agent,
                        raw_output, validator_result
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(),
                        action_id,
                        current_tick,
                        character_id,
                        Jsonb(proposed_action),
                        f"rejected: {exc}",
                    ),
                )

                return {
                    "accepted": False,
                    "duplicate": False,
                    "reason": str(exc),
                }

            # Calculate the new canonical state hash.
            digest = state_hash(updated)

            # Record the decision.
            cur.execute(
                """
                INSERT INTO decisions (
                    id, action_id, tick_id, agent,
                    raw_output, validator_result
                )
                VALUES (%s, %s, %s, %s, %s, 'accepted')
                """,
                (
                    uuid4(),
                    action_id,
                    current_tick,
                    character_id,
                    Jsonb(proposed_action),
                ),
            )

            # Append the accepted event.
            cur.execute(
                """
                INSERT INTO events (
                    action_id, tick_id, actor,
                    type, payload, rules_version
                )
                VALUES (%s, %s, %s, %s, %s, 1)
                RETURNING id
                """,
                (
                    action_id,
                    current_tick,
                    character_id,
                    "MOVE_STARTED",
                    Jsonb({
                        "from": state["characters"][character_id]["location"],
                        "to": destination,
                        "start_tick": current_tick,
                        "duration_ticks": duration_ticks,
                    }),
                ),
            )

            event_id = cur.fetchone()[0]

            # Update the projection in the SAME transaction.
            cur.execute(
                """
                UPDATE world_state
                SET state = %s,
                    state_hash = %s,
                    last_event_id = %s
                WHERE id = 1
                """,
                (
                    Jsonb(updated),
                    digest,
                    event_id,
                ),
            )

            return {
                "accepted": True,
                "duplicate": False,
                "event_id": event_id,
                "state_hash": digest,
            }
