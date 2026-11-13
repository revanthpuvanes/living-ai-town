"""Continuous Living AI Town production worker."""

import os
import signal
import sys
import time
from urllib.parse import urlparse

from app.agents.scheduler import run_cycle
from app.db.repository import get_world_state


INTERVAL_SECONDS = 10
EXPECTED_DATABASE = "ai_town_prod"


def main():
    database_url = os.getenv("DATABASE_URL", "")
    database_name = urlparse(database_url).path.lstrip("/")

    if database_name != EXPECTED_DATABASE:
        raise SystemExit(
            "Production worker requires database: "
            + EXPECTED_DATABASE
        )

    if os.getenv("AI_TOWN_ENABLE_LLM") != "1":
        raise SystemExit(
            "Production worker requires AI_TOWN_ENABLE_LLM=1"
        )

    if not os.getenv("MISTRAL_API_KEY"):
        raise SystemExit("MISTRAL_API_KEY is required")

    stopping = False

    def stop_handler(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    print("Living AI Town production worker started", flush=True)
    print("Starting tick:", get_world_state()["tick"], flush=True)
    print("Interval: 10 seconds", flush=True)

    while not stopping:
        started = time.monotonic()

        try:
            result = run_cycle(execute=True)
            print(
                f"Tick {result.start_tick} -> {result.end_tick}, "
                f"conversations: {len(result.interaction_results)}",
                flush=True,
            )
        except Exception as exc:
            print(
                f"Cycle error: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )

        while not stopping:
            remaining = INTERVAL_SECONDS - (
                time.monotonic() - started
            )
            if remaining <= 0:
                break
            time.sleep(min(0.2, remaining))

    print("Worker stopped safely", flush=True)


if __name__ == "__main__":
    main()
