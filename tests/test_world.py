import pytest

from app.engine.world import (
    InvalidAction,
    advance_tick,
    initial_state,
    start_move,
    state_hash,
)


def simulate():
    state = initial_state()

    state = start_move(state, "emma", "shop", 3)
    state = start_move(state, "noah", "square", 2)

    for _ in range(5):
        state = advance_tick(state)

    return state


def test_determinism():
    first = simulate()
    second = simulate()

    assert first == second
    assert state_hash(first) == state_hash(second)


def test_initial_state():
    state = initial_state()

    assert state["tick"] == 0
    assert len(state["characters"]) == 3
    assert len(state["locations"]) == 4


def test_movement_duration():
    state = initial_state()
    state = start_move(state, "emma", "shop", 3)

    for _ in range(2):
        state = advance_tick(state)
        assert state["characters"]["emma"]["location"] == "bakery"

    state = advance_tick(state)

    assert state["characters"]["emma"]["location"] == "shop"
    assert state["characters"]["emma"]["movement"] is None


def test_invalid_action_does_not_mutate_state():
    state = initial_state()
    before = state_hash(state)

    with pytest.raises(InvalidAction):
        start_move(state, "emma", "unknown", 2)

    assert state_hash(state) == before


def test_double_movement_rejected():
    state = initial_state()
    state = start_move(state, "emma", "shop", 3)

    with pytest.raises(InvalidAction):
        start_move(state, "emma", "square", 2)


def test_original_state_not_mutated():
    original = initial_state()
    before = state_hash(original)

    updated = start_move(original, "emma", "shop", 3)

    assert state_hash(original) == before
    assert updated != original
