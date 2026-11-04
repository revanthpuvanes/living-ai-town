import os
import subprocess
import sys
from uuid import uuid4

import psycopg


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)
TEST_DB = f"ai_town_budget_{uuid4().hex[:12]}"
TEST_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{TEST_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {TEST_DB}")

    try:
        with psycopg.connect(TEST_URL) as conn:
            conn.execute("""
                CREATE TABLE llm_request_budget (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    max_requests INTEGER NOT NULL
                        CHECK (max_requests >= 0),
                    used_requests INTEGER NOT NULL DEFAULT 0
                        CHECK (used_requests >= 0),
                    CHECK (used_requests <= max_requests)
                )
            """)
            conn.execute("""
                INSERT INTO llm_request_budget
                    (id, max_requests, used_requests)
                VALUES (1, 5, 0)
            """)

        env = {**os.environ, "DATABASE_URL": TEST_URL}

        code = '''
from concurrent.futures import ThreadPoolExecutor

from app.llm.budget import (
    get_llm_budget,
    reserve_llm_request,
)


with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(
        pool.map(lambda _: reserve_llm_request(), range(10))
    )

assert results.count(True) == 5, results
assert results.count(False) == 5, results

budget = get_llm_budget()

assert budget["used_requests"] == 5
assert budget["remaining_requests"] == 0
assert reserve_llm_request() is False

print("SUCCESSFUL RESERVATIONS:", results.count(True))
print("REJECTED RESERVATIONS:", results.count(False))
print("CONCURRENT BUDGET: PASSED")
'''

        subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            check=True,
        )

    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
            """, (TEST_DB,))
            conn.execute(f"DROP DATABASE {TEST_DB}")

        print("Temporary database cleaned up")


if __name__ == "__main__":
    main()
