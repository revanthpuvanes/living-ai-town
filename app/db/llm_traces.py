from dataclasses import dataclass
from uuid import UUID

from app.db.connection import get_connection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.client import DialogueGeneration


@dataclass(frozen=True)
class LLMTrace:
    id: int
    action_id: UUID
    event_id: int | None
    tick_id: int
    speaker: str
    listener: str
    source: str
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: float | None
    error: str | None


TRACE_COLUMNS = """
    id, action_id, event_id, tick_id,
    speaker, listener, source, model,
    prompt_tokens, completion_tokens,
    total_tokens, latency_ms, error
"""


def _from_row(row):
    return LLMTrace(*row)


def get_llm_trace(action_id: UUID):
    with get_connection() as conn:
        row = conn.execute(
            f"""
            SELECT {TRACE_COLUMNS}
            FROM llm_traces
            WHERE action_id = %s
            """,
            (action_id,),
        ).fetchone()

    return _from_row(row) if row else None


def record_llm_trace(
    *,
    action_id: UUID,
    tick_id: int,
    speaker: str,
    listener: str,
    generation: "DialogueGeneration",
    event_id: int | None = None,
    conn=None,
):
    if generation.source not in ("mistral", "fallback"):
        raise ValueError("Unsupported generation source")

    def insert(connection):
        row = connection.execute(
            f"""
            INSERT INTO llm_traces (
                action_id, event_id, tick_id,
                speaker, listener, source, model,
                prompt_tokens, completion_tokens,
                total_tokens, latency_ms, error
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (action_id) DO NOTHING
            RETURNING {TRACE_COLUMNS}
            """,
            (
                action_id,
                event_id,
                tick_id,
                speaker,
                listener,
                generation.source,
                generation.model,
                generation.prompt_tokens,
                generation.completion_tokens,
                generation.total_tokens,
                generation.latency_ms,
                generation.error,
            ),
        ).fetchone()

        if row is None:
            row = connection.execute(
                f"""
                SELECT {TRACE_COLUMNS}
                FROM llm_traces
                WHERE action_id = %s
                """,
                (action_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError("LLM trace was not persisted")

        return _from_row(row)

    if conn is not None:
        return insert(conn)

    with get_connection() as connection:
        return insert(connection)


def link_llm_trace_event(action_id: UUID, event_id: int):
    with get_connection() as conn:
        row = conn.execute(
            f"""
            UPDATE llm_traces
            SET event_id = %s
            WHERE action_id = %s
              AND (event_id IS NULL OR event_id = %s)
            RETURNING {TRACE_COLUMNS}
            """,
            (event_id, action_id, event_id),
        ).fetchone()

    if row is None:
        raise ValueError(
            "Trace missing or already linked to another event"
        )

    return _from_row(row)
