from uuid import uuid4

from app.db.repository import get_world_state, record_move
from app.engine.world import InvalidAction


def main():
    before = get_world_state()

    print("Starting tick:", before["tick"])

    # Deliberately stale tick.
    try:
        record_move(
            action_id=uuid4(),
            character_id="emma",
            destination="bakery",
            duration_ticks=3,
            expected_tick=before["tick"] - 1,
            expected_state_hash=before["state_hash"],
        )
    except InvalidAction as exc:
        assert "Stale observation" in str(exc)
        print("Stale tick rejected:", exc)
    else:
        raise AssertionError("Stale tick was accepted")

    # Current tick, deliberately incorrect state hash.
    try:
        record_move(
            action_id=uuid4(),
            character_id="emma",
            destination="bakery",
            duration_ticks=3,
            expected_tick=before["tick"],
            expected_state_hash="0" * 64,
        )
    except InvalidAction as exc:
        assert "Stale observation" in str(exc)
        print("Stale state hash rejected:", exc)
    else:
        raise AssertionError("Stale state hash was accepted")

    after = get_world_state()

    assert after["tick"] == before["tick"]
    assert after["state_hash"] == before["state_hash"]
    assert after["state"] == before["state"]

    print("Authoritative world unchanged: YES")
    print("STALE OBSERVATION TESTS: PASSED")


if __name__ == "__main__":
    main()
