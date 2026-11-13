"""Run the Living AI Town simulation on a controlled schedule."""

import argparse
import os
import signal
import sys
import time

from app.agents.scheduler import run_cycle
from app.db.repository import get_world_state
from app.llm.budget import get_llm_budget


def main():
    parser = argparse.ArgumentParser(
        description="Living AI Town simulation worker"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between cycles (minimum: 1)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Number of cycles before stopping (0 = unlimited)",
    )
    args = parser.parse_args()

    if args.interval < 1:
        parser.error("--interval must be at least 1 second")

    if args.max_cycles < 0:
        parser.error("--max-cycles cannot be negative")

    if os.getenv("AI_TOWN_ENABLE_LLM") != "0":
        raise SystemExit(
            "Worker safety check: set AI_TOWN_ENABLE_LLM=0"
        )

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    if os.path.isfile(".game-demo-db"):
        with open(".game-demo-db", encoding="utf-8") as file:
            demo_url = file.read().strip()

        if database_url != demo_url:
            raise SystemExit(
                "Worker safety check: DATABASE_URL is not the demo database"
            )
    else:
        raise SystemExit("Missing .game-demo-db safety marker")

    stopping = False

    def stop_handler(signum, frame):
        nonlocal stopping
        stopping = True
        print("\nShutdown requested. Finishing safely...", flush=True)

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    print("=== LIVING AI TOWN WORKER ===", flush=True)
    print("Starting tick:", get_world_state()["tick"], flush=True)
    print("Interval:", args.interval, "seconds", flush=True)
    print("Max cycles:", args.max_cycles, flush=True)
    print("LLM: DISABLED", flush=True)

    initial_budget = get_llm_budget()
    completed = 0

    while not stopping:
        if args.max_cycles and completed >= args.max_cycles:
            break

        try:
            result = run_cycle(execute=True)
        except Exception as exc:
            print(
                f"Worker stopped: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return 1

        completed += 1

        print(
            f"Cycle {completed}: "
            f"tick {result.start_tick} -> {result.end_tick}",
            flush=True,
        )

        for agent in result.agent_results:
            print(
                f"  {agent.character_id}: {agent.action}",
                flush=True,
            )

        for interaction in result.interaction_results:
            print(
                f"  Conversation: "
                f"{interaction.speaker} -> {interaction.listener}",
                flush=True,
            )

        if stopping:
            break

        if args.max_cycles and completed >= args.max_cycles:
            break

        deadline = time.monotonic() + args.interval
        while not stopping:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.2, remaining))

    final_budget = get_llm_budget()

    if final_budget != initial_budget:
        print(
            "WARNING: LLM budget changed during worker execution",
            file=sys.stderr,
        )
        return 1

    print("=== WORKER STOPPED ===", flush=True)
    print("Completed cycles:", completed, flush=True)
    print("Final tick:", get_world_state()["tick"], flush=True)
    print("LLM requests spent: 0", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
