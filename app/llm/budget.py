from app.db.connection import get_connection


def reserve_llm_request() -> bool:
    """Atomically reserve one request before an external API call."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE llm_request_budget
                SET used_requests = used_requests + 1
                WHERE id = 1
                  AND used_requests < max_requests
                RETURNING used_requests
            """)

            return cur.fetchone() is not None


def get_llm_budget() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT max_requests, used_requests
                FROM llm_request_budget
                WHERE id = 1
            """)

            row = cur.fetchone()

            if row is None:
                raise RuntimeError("LLM budget not initialized")

            return {
                "max_requests": row[0],
                "used_requests": row[1],
                "remaining_requests": row[0] - row[1],
            }
