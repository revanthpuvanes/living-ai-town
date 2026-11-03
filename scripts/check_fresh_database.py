import os
from pathlib import Path

import psycopg

from app.db.repository import initialize_world, get_world_state

ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = "ai_town_bootstrap_check"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    original_url = os.environ.get("DATABASE_URL")

    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (TEST_DB,),
            )
            if cur.fetchone():
                raise RuntimeError(
                    f"{TEST_DB} already exists; refusing to overwrite it"
                )
            cur.execute(f"CREATE DATABASE {TEST_DB}")

    print("Temporary database created")

    try:
        with psycopg.connect(TEST_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(Path("db/init/001_schema.sql").read_text())

        print("Initial schema applied")

        os.environ["DATABASE_URL"] = TEST_URL

        from scripts.migrate import main as migrate_main
        import scripts.migrate as migrations

        migrations.DATABASE_URL = TEST_URL
        migrate_main()

        with psycopg.connect(TEST_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'decisions'
                              AND column_name = 'action_id'
                        ),
                        EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'ticks'
                              AND column_name = 'request_id'
                        ),
                        EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE indexname = 'idx_decisions_action_id'
                        ),
                        EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE indexname = 'ticks_request_id_unique'
                        )
                """)
                checks = cur.fetchone()
                assert all(checks), checks

        print("Required columns and indexes: PRESENT")

        import subprocess
        import sys

        verification_code = """
from app.db.repository import initialize_world, get_world_state
from app.db.simulation import advance_world_tick
from app.db.snapshots import create_snapshot, verify_replay

initialize_world()
world = get_world_state()

assert world["tick"] == 0, world
print("World initialized at tick 0: YES")

result = advance_world_tick()
assert result["tick"] == 1
print("First tick advanced: YES")

create_snapshot()
replay = verify_replay()

assert (
    replay["full_hash"]
    == replay["snapshot_hash"]
    == replay["live_hash"]
)
print("Fresh database replay: PASSED")
"""

        subprocess.run(
            [sys.executable, "-c", verification_code],
            env={**os.environ, "DATABASE_URL": TEST_URL},
            check=True,
        )

        print("\nFRESH DATABASE BOOTSTRAP: PASSED")

    finally:
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url

        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            with admin.cursor() as cur:
                cur.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                """, (TEST_DB,))
                cur.execute(f"DROP DATABASE {TEST_DB}")

        print("Temporary test database cleaned up")


if __name__ == "__main__":
    main()
