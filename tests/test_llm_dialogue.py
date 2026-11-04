import json

import pytest

from app.llm.dialogue import (
    InvalidDialogue,
    validate_dialogue,
)


def test_valid_dialogue():
    result = validate_dialogue(json.dumps({
        "message": "Hello Noah!",
        "emotion": "friendly",
    }))

    assert result.message == "Hello Noah!"
    assert result.emotion == "friendly"


@pytest.mark.parametrize("raw", [
    "not json",
    "[]",
    "{}",
    '{"message": "", "emotion": "friendly"}',
    '{"message": "Hi", "emotion": "angry"}',
    '{"message": 123, "emotion": "friendly"}',
    '{"message": "Hi", "emotion": 42}',
    '{"message": "Hi", "emotion": "friendly", "extra": true}',
    json.dumps({
        "message": "x" * 501,
        "emotion": "friendly",
    }),
])
def test_invalid_dialogue(raw):
    with pytest.raises(InvalidDialogue):
        validate_dialogue(raw)


def test_whitespace_is_trimmed():
    result = validate_dialogue(json.dumps({
        "message": "  Hello Sophia!  ",
        "emotion": "curious",
    }))

    assert result.message == "Hello Sophia!"
