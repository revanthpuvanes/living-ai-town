import json
from dataclasses import dataclass

ALLOWED_EMOTIONS = {
    "friendly",
    "curious",
    "excited",
    "concerned",
    "neutral",
}


class InvalidDialogue(ValueError):
    pass


@dataclass(frozen=True)
class DialogueResponse:
    message: str
    emotion: str


def validate_dialogue(raw: str) -> DialogueResponse:
    if not isinstance(raw, str):
        raise InvalidDialogue("LLM response must be a string")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidDialogue("Invalid JSON") from exc

    if not isinstance(data, dict):
        raise InvalidDialogue("Expected a JSON object")

    if set(data) != {"message", "emotion"}:
        raise InvalidDialogue(
            "Expected exactly message and emotion"
        )

    message = data["message"]
    emotion = data["emotion"]

    if not isinstance(message, str):
        raise InvalidDialogue("Message must be a string")

    message = message.strip()

    if not message:
        raise InvalidDialogue("Message cannot be empty")

    if len(message) > 500:
        raise InvalidDialogue("Message exceeds 500 characters")

    if not isinstance(emotion, str):
        raise InvalidDialogue("Emotion must be a string")

    if emotion not in ALLOWED_EMOTIONS:
        raise InvalidDialogue("Unsupported emotion")

    return DialogueResponse(
        message=message,
        emotion=emotion,
    )
