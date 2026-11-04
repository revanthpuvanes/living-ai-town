from app.agents.scheduler import run_cycle
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay


def main():
    before = get_world_state()
    assert before["tick"] == 24, (
        f"Expected tick 24, got {before['tick']}"
    )

    moves = []

    for cycle in range(24):
        result = run_cycle(execute=True)

        assert result.end_tick == result.start_tick + 1
        assert result.tick_result["duplicate"] is False

        for agent_result in result.agent_results:
            if agent_result.action == "MOVE":
                assert agent_result.result["accepted"]
                moves.append((
                    result.start_tick,
                    agent_result.character_id,
                ))

        print(
            f"Tick {result.end_tick}:",
            ", ".join(
                f"{agent}:{action}"
                for agent, action in (
                    (r.character_id, r.action)
                    for r in result.agent_results
                )
            ),
        )

    after = get_world_state()
    assert after["tick"] == 48

    print("\n=== AUTONOMOUS MOVEMENTS ===")
    for tick, agent in moves:
        print(f"Tick {tick}: {agent} started moving")

    assert len(moves) >= 4, (
        f"Expected multiple daily movements, got {len(moves)}"
    )

    print("\n=== FINAL WORLD ===")
    for agent_id, character in after["state"]["characters"].items():
        print(
            agent_id,
            character["location"],
            character["activity"],
        )

    replay = verify_replay()
    assert (
        replay["full_hash"]
        == replay["snapshot_hash"]
        == replay["live_hash"]
    )

    print("\nFULL DAY SIMULATION: PASSED")
    print("REPLAY VERIFICATION: PASSED")


if __name__ == "__main__":
    main()
