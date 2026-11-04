CREATE TABLE llm_traces (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    action_id UUID NOT NULL UNIQUE,

    event_id BIGINT UNIQUE
        REFERENCES events(id),

    tick_id BIGINT NOT NULL
        REFERENCES ticks(id),

    speaker TEXT NOT NULL,
    listener TEXT NOT NULL,

    source TEXT NOT NULL
        CHECK (source IN ('mistral', 'fallback')),

    model TEXT,

    prompt_tokens INTEGER
        CHECK (prompt_tokens >= 0),

    completion_tokens INTEGER
        CHECK (completion_tokens >= 0),

    total_tokens INTEGER
        CHECK (total_tokens >= 0),

    latency_ms DOUBLE PRECISION
        CHECK (latency_ms >= 0),

    error TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        total_tokens IS NULL
        OR prompt_tokens IS NULL
        OR completion_tokens IS NULL
        OR total_tokens = prompt_tokens + completion_tokens
    )
);

CREATE INDEX idx_llm_traces_tick
    ON llm_traces(tick_id, id);

CREATE INDEX idx_llm_traces_source
    ON llm_traces(source, created_at);
