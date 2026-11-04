from dataclasses import dataclass

from app.db.conversations import get_recent_conversations
from app.db.repository import get_world_state


AGENT_PROFILES = {
    "emma": {
        "name": "Emma",
        "role": "baker",
        "workplace": "bakery",
        "personality": "warm, practical, and community-minded",
    },
    "noah": {
        "name": "Noah",
        "role": "teacher",
        "workplace": "school",
        "personality": "thoughtful, curious, and patient",
    },
    "sophia": {
        "name": "Sophia",
        "role": "shopkeeper",
        "workplace": "shop",
        "personality": "friendly, observant, and entrepreneurial",
    },
}


@dataclass(frozen=True)
class DialogueContext:
    speaker_id: str
    listener_id: str
    tick: int
    location: str
    speaker_profile: dict
    listener_profile: dict
    recent_conversations: tuple


def build_dialogue_context(
    speaker_id: str,
    listener_id: str,
    *,
    history_limit: int = 5,
) -> DialogueContext:
    if speaker_id not in AGENT_PROFILES:
        raise ValueError("Unknown speaker")

    if listener_id not in AGENT_PROFILES:
        raise ValueError("Unknown listener")

    if speaker_id == listener_id:
        raise ValueError("Speaker and listener must differ")

    if not 0 <= history_limit <= 20:
        raise ValueError("History limit must be between 0 and 20")

    world = get_world_state()
    characters = world["state"]["characters"]

    speaker = characters[speaker_id]
    listener = characters[listener_id]

    if speaker["movement"] is not None:
        raise ValueError("Speaker is moving")

    if listener["movement"] is not None:
        raise ValueError("Listener is moving")

    if speaker["location"] != listener["location"]:
        raise ValueError("Characters are not together")

    history = []

    if history_limit:
        for item in get_recent_conversations(
            speaker_id,
            limit=20,
        ):
            pair = {item["speaker"], item["listener"]}

            if pair == {speaker_id, listener_id}:
                history.append(item)

            if len(history) >= history_limit:
                break

    return DialogueContext(
        speaker_id=speaker_id,
        listener_id=listener_id,
        tick=world["tick"],
        location=speaker["location"],
        speaker_profile=AGENT_PROFILES[speaker_id].copy(),
        listener_profile=AGENT_PROFILES[listener_id].copy(),
        recent_conversations=tuple(history),
    )
