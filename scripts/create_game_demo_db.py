import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql


ADMIN_URL = (
    "postgresql://town:local_dev_only@127.0.0.1:5433/postgres"
)

DEMO_DB = f"ai_town_demo_{uuid4().hex[:12]}"

DEMO_URL = (
    f"postgresql://town:local_dev_only@127.0.0.1:5433/{DEMO_DB}"
)


def main():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(DEMO_DB)
            )
        )

    try:
        with open("db/init/001_schema.sql") as file:
            schema = file.read()

        with psycopg.connect(DEMO_URL) as conn:
            conn.execute(schema)

        env = {
            **os.environ,
            "DATABASE_URL": DEMO_URL,
            "AI_TOWN_ENABLE_LLM": "0",
        }

        subprocess.run(
            [sys.executable, "-m", "scripts.migrate"],
            env=env,
            check=True,
        )

        subprocess.run(
            [
                sys.executable,
                "-c",
                "from app.db.repository import initialize_world; "
                "initialize_world(); "
                "print('DEMO WORLD INITIALIZED: PASSED')",
            ],
            env=env,
            check=True,
        )

        with open(".game-demo-db", "w") as file:
            file.write(DEMO_URL + "\n")

        print("DEMO DATABASE CREATED:", DEMO_DB)
        print("DEMO DATABASE URL SAVED TO .game-demo-db")

    except Exception:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    sql.Identifier(DEMO_DB)
                )
            )
        raise


if __name__ == "__main__":
    main()
