from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from app.db.visitor_messages import record_visitor_message
from fastapi.responses import JSONResponse

from app.db.connection import get_connection
from app.db.repository import get_world_state


app = FastAPI(
    title="Living AI Town API",
    description="Read-only API for the persistent AI town simulation.",
    version="0.1.0",
)


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")

        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable"},
        )


@app.get("/api/world")
def world():
    try:
        return get_world_state()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="World not initialized",
        )


@app.get("/api/events")
def events(
    limit: int = Query(default=30, ge=1, le=100),
):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tick_id, actor, type, payload,
                   depends_on, rules_version, created_at
            FROM events
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return {
        "events": [
            {
                "id": row[0],
                "tick": row[1],
                "actor": row[2],
                "type": row[3],
                "payload": row[4],
                "depends_on": row[5],
                "rules_version": row[6],
                "created_at": row[7].isoformat(),
            }
            for row in rows
        ]
    }


class VisitorMessageRequest(BaseModel):
    character_id: str
    message: str = Field(min_length=1, max_length=300)


@app.post("/api/visitor-message", status_code=201)
def visitor_message(request: VisitorMessageRequest):
    try:
        return record_visitor_message(
            request.character_id,
            request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="World not initialized",
        )
