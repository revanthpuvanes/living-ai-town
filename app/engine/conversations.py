from app.engine.world import InvalidAction


MAX_MESSAGE_LENGTH = 500


def validate_conversation(
    state: dict,
    speaker_id: str,
    listener_id: str,
    message: str,
) -> None:
    characters = state["characters"]

    if speaker_id not in characters:
        raise InvalidAction("Unknown speaker")

    if listener_id not in characters:
        raise InvalidAction("Unknown listener")

    if speaker_id == listener_id:
        raise InvalidAction("Cannot speak to yourself")

    if not isinstance(message, str):
        raise InvalidAction("Message must be a string")

    if not message.strip():
        raise InvalidAction("Message cannot be empty")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise InvalidAction("Message exceeds maximum length")

    speaker = characters[speaker_id]
    listener = characters[listener_id]

    if speaker["movement"] is not None:
        raise InvalidAction("Speaker is moving")

    if listener["movement"] is not None:
        raise InvalidAction("Listener is moving")

    if speaker["location"] != listener["location"]:
        raise InvalidAction("Characters are not co-located")


def apply_conversation(state: dict, event: dict) -> dict:
    """
    Conversation events do not change physical world state.

    They are persisted separately in the event log.
    """
    payload = event["payload"]

    validate_conversation(
        state,
        event["actor"],
        payload["listener"],
        payload["message"],
    )

    if payload["tick"] != state["tick"]:
        raise ValueError("Conversation tick mismatch")

    if payload["location"] != state["characters"][event["actor"]]["location"]:
        raise ValueError("Conversation location mismatch")

    return state
