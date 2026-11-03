import hashlib
import os
from pathlib import Path

import psycopg

MIGRATIONS = Path("db/migrations")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://town:local_dev_only@127.0.0.1:5433/ai_town",
)


def main():
    files = sorted(MIGRATIONS.glob("*.sql"))

    if not files:
        raise RuntimeError("No migration files found")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Serialize concurrent migration runners.
            cur.execute("SELECT pg_advisory_xact_lock(78234109)")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            for path in files:
                version = path.name
                sql = path.read_text()
                checksum = hashlib.sha256(
                    sql.encode("utf-8")
                ).hexdigest()

                cur.execute("""
                    SELECT checksum
                    FROM schema_migrations
                    WHERE version = %s
                """, (version,))

                existing = cur.fetchone()

                if existing:
                    if existing[0] != checksum:
                        raise RuntimeError(
                            f"Migration changed after application: {version}"
                        )
                    print(f"SKIP {version}")
                    continue

                print(f"APPLY {version}")
                cur.execute(sql)

                cur.execute("""
                    INSERT INTO schema_migrations (
                        version, checksum
                    )
                    VALUES (%s, %s)
                """, (version, checksum))

            print("MIGRATIONS: PASSED")


if __name__ == "__main__":
    main()
