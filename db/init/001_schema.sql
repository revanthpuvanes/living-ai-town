CREATE TABLE ticks (
    id BIGINT PRIMARY KEY CHECK (id >= 0),
    status TEXT NOT NULL
        CHECK (status IN ('running', 'completed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    state_hash CHAR(64),
    CHECK (
        (status = 'running'
            AND completed_at IS NULL
            AND state_hash IS NULL)
        OR
        (status = 'completed'
            AND completed_at IS NOT NULL
            AND state_hash IS NOT NULL)
    )
);

CREATE TABLE decisions (
    id UUID PRIMARY KEY,
    tick_id BIGINT NOT NULL REFERENCES ticks(id),
    agent TEXT NOT NULL,
    context_ref TEXT,
    raw_output JSONB,
    validator_result TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0
        CHECK (tokens_in >= 0),
    tokens_out INTEGER NOT NULL DEFAULT 0
        CHECK (tokens_out >= 0),
    cost_microunits BIGINT NOT NULL DEFAULT 0
        CHECK (cost_microunits >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action_id UUID NOT NULL UNIQUE,
    tick_id BIGINT NOT NULL REFERENCES ticks(id),
    actor TEXT NOT NULL,
    type TEXT NOT NULL,
    payload JSONB NOT NULL,
    depends_on BIGINT[] NOT NULL DEFAULT '{}',
    rules_version INTEGER NOT NULL CHECK (rules_version > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_tick_id
    ON events(tick_id, id);

CREATE TABLE event_context (
    event_id BIGINT NOT NULL REFERENCES events(id),
    seen_event_id BIGINT NOT NULL REFERENCES events(id),
    PRIMARY KEY (event_id, seen_event_id),
    CHECK (event_id <> seen_event_id)
);

CREATE TABLE world_state (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    current_tick BIGINT NOT NULL DEFAULT 0
        CHECK (current_tick >= 0),
    rules_version INTEGER NOT NULL DEFAULT 1,
    state JSONB NOT NULL,
    state_hash CHAR(64) NOT NULL,
    last_event_id BIGINT REFERENCES events(id)
);

CREATE TABLE snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tick_id BIGINT NOT NULL UNIQUE REFERENCES ticks(id),
    last_event_id BIGINT REFERENCES events(id),
    rules_version INTEGER NOT NULL,
    state JSONB NOT NULL,
    state_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION reject_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Accepted events are append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_append_only
BEFORE UPDATE OR DELETE ON events
FOR EACH ROW
EXECUTE FUNCTION reject_event_mutation();
