import argparse
from pprint import pprint

from app.agents.runner import run_agent_once
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--agent",
        choices=("emma", "noah", "sophia"),
        required=True,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the decision; default is read-only",
    )
    args = parser.parse_args()

    if not args.execute:
        from app.agents.decisions import DeterministicAgent
        from app.agents.observations import observe_character

        observation = observe_character(args.agent)
        decision = DeterministicAgent().decide(observation)

        print("DRY RUN — no database writes")
        print("Observation:")
        pprint(observation)
        print("Decision:")
        pprint(decision)
        return

    print("EXECUTING AGENT:", args.agent)
    result = run_agent_once(args.agent)
    pprint(result)

    world = get_world_state()
    print("Current tick:", world["tick"])
    print("Character state:")
    pprint(world["state"]["characters"][args.agent])

    replay = verify_replay()
    assert (
        replay["full_hash"]
        == replay["snapshot_hash"]
        == replay["live_hash"]
    )
    print("REPLAY VERIFICATION: PASSED")


if __name__ == "__main__":
    main()
