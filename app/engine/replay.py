from app.engine.world import (
    RULES_VERSION,
    advance_tick,
    initial_state,
    start_move,
    state_hash,
)


def apply_event(state, event):
    if event["rules_version"] != RULES_VERSION:
        raise ValueError("Incompatible rules version")

    event_type = event["type"]
    payload = event["payload"]

    if event_type == "MOVE_STARTED":
        character_id = event["actor"]
        character = state["characters"][character_id]

        if character["location"] != payload["from"]:
            raise ValueError("Movement origin mismatch")

        if state["tick"] != payload["start_tick"]:
            raise ValueError("Movement tick mismatch")

        return start_move(
            state,
            character_id,
            payload["to"],
            payload["duration_ticks"],
        )

    if event_type == "TICK_ADVANCED":
        if payload["tick"] != state["tick"] + 1:
            raise ValueError("Unexpected tick sequence")

        return advance_tick(state)

    raise ValueError(f"Unknown event type: {event_type}")


def replay_events(events):
    state = initial_state()

    for event in events:
        state = apply_event(state, event)

    return state
