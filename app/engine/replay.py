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

    if event_type == "CONVERSATION_SPOKEN":
        from app.engine.conversations import apply_conversation
        return apply_conversation(state, event)

    if event_type == "VISITOR_MESSAGE":
        if event["actor"] != "visitor":
            raise ValueError("Invalid visitor event actor")

        if payload["tick"] != state["tick"]:
            raise ValueError("Visitor message tick mismatch")

        if payload["character_id"] not in state["characters"]:
            raise ValueError("Unknown visitor message recipient")

        message = payload["message"]

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Invalid visitor message")

        if len(message) > 300:
            raise ValueError("Visitor message too long")

        # Visitor messages are logged but do not mutate physical state.
        return state

    if event_type == "VISITOR_REPLY":
        if event["actor"] not in state["characters"]:
            raise ValueError("Unknown visitor reply character")

        if payload["tick"] != state["tick"]:
            raise ValueError("Visitor reply tick mismatch")

        if not isinstance(payload["message"], str):
            raise ValueError("Invalid visitor reply")

        if not payload["message"].strip():
            raise ValueError("Empty visitor reply")

        if not isinstance(payload["visitor_event_id"], int):
            raise ValueError("Invalid visitor trace reference")

        return state

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
