import pytest

from app.engine.conversations import (
    apply_conversation,
    validate_conversation,
)
from app.engine.world import InvalidAction, initial_state, state_hash


def colocated_state():
    state = initial_state()
    state["characters"]["emma"]["location"] = "square"
    state["characters"]["noah"]["location"] = "square"
    return state


def test_valid_conversation():
    state = colocated_state()
    validate_conversation(state, "emma", "noah", "Hello Noah!")


def test_conversation_does_not_change_world():
    state = colocated_state()
    before = state_hash(state)

    event = {
        "actor": "emma",
        "payload": {
            "listener": "noah",
            "message": "Hello Noah!",
            "tick": 0,
            "location": "square",
        },
    }

    result = apply_conversation(state, event)

    assert state_hash(result) == before


def test_different_locations_rejected():
    with pytest.raises(InvalidAction, match="not co-located"):
        validate_conversation(
            initial_state(), "emma", "noah", "Hello"
        )


def test_self_conversation_rejected():
    with pytest.raises(InvalidAction, match="yourself"):
        validate_conversation(
            colocated_state(), "emma", "emma", "Hello"
        )


def test_empty_message_rejected():
    with pytest.raises(InvalidAction, match="empty"):
        validate_conversation(
            colocated_state(), "emma", "noah", " "
        )


def test_oversized_message_rejected():
    with pytest.raises(InvalidAction, match="maximum"):
        validate_conversation(
            colocated_state(), "emma", "noah", "x" * 501
        )


def test_unknown_speaker_rejected():
    with pytest.raises(InvalidAction, match="Unknown speaker"):
        validate_conversation(
            colocated_state(), "unknown", "noah", "Hello"
        )


def test_unknown_listener_rejected():
    with pytest.raises(InvalidAction, match="Unknown listener"):
        validate_conversation(
            colocated_state(), "emma", "unknown", "Hello"
        )


def test_tick_mismatch_rejected():
    state = colocated_state()
    event = {
        "actor": "emma",
        "payload": {
            "listener": "noah",
            "message": "Hello",
            "tick": 99,
            "location": "square",
        },
    }
    with pytest.raises(ValueError, match="tick mismatch"):
        apply_conversation(state, event)


def test_location_mismatch_rejected():
    state = colocated_state()
    event = {
        "actor": "emma",
        "payload": {
            "listener": "noah",
            "message": "Hello",
            "tick": 0,
            "location": "bakery",
        },
    }
    with pytest.raises(ValueError, match="location mismatch"):
        apply_conversation(state, event)
