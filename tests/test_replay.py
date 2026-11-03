import pytest

from app.engine.replay import apply_event, replay_events
from app.engine.world import initial_state, state_hash


def test_replay_matches_direct_simulation():
    events = [
        {
            "actor": "emma",
            "type": "MOVE_STARTED",
            "payload": {
                "from": "bakery",
                "to": "square",
                "start_tick": 0,
                "duration_ticks": 3,
            },
            "rules_version": 1,
        },
        *[
            {
                "actor": "system",
                "type": "TICK_ADVANCED",
                "payload": {"tick": tick},
                "rules_version": 1,
            }
            for tick in range(1, 4)
        ],
    ]

    replayed = replay_events(events)

    assert replayed["tick"] == 3
    assert replayed["characters"]["emma"]["location"] == "square"
    assert replayed["characters"]["emma"]["movement"] is None
    assert state_hash(replayed) == state_hash(replay_events(events))


def test_incompatible_rules_version():
    event = {
        "actor": "system",
        "type": "TICK_ADVANCED",
        "payload": {"tick": 1},
        "rules_version": 999,
    }

    with pytest.raises(ValueError, match="Incompatible"):
        apply_event(initial_state(), event)


def test_missing_tick_detected():
    event = {
        "actor": "system",
        "type": "TICK_ADVANCED",
        "payload": {"tick": 2},
        "rules_version": 1,
    }

    with pytest.raises(ValueError, match="Unexpected tick"):
        apply_event(initial_state(), event)
