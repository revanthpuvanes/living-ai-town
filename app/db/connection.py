import os

import psycopg


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://town:local_dev_only@127.0.0.1:5433/ai_town",
)


def get_connection():
    return psycopg.connect(DATABASE_URL)


def check_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            return cur.fetchone()
