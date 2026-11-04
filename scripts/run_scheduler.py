import argparse
from pprint import pprint

from app.agents.scheduler import run_cycle
from app.db.repository import get_world_state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persist decisions and advance one tick",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
    )
    args = parser.parse_args()

    if not 1 <= args.cycles <= 100:
        parser.error("--cycles must be between 1 and 100")

    if not args.execute and args.cycles != 1:
        parser.error("Multiple cycles require --execute")

    for index in range(args.cycles):
        result = run_cycle(execute=args.execute)
        print(f"\n=== CYCLE {index + 1} ===")
        pprint(result)

    world = get_world_state()
    print("\n=== WORLD STATE ===")
    print("Tick:", world["tick"])

    for agent_id, character in world["state"]["characters"].items():
        print(
            agent_id,
            "location=", character["location"],
            "activity=", character["activity"],
        )


if __name__ == "__main__":
    main()
