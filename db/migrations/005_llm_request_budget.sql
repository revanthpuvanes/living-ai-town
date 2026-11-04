CREATE TABLE llm_request_budget (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    max_requests INTEGER NOT NULL CHECK (max_requests >= 0),
    used_requests INTEGER NOT NULL DEFAULT 0
        CHECK (used_requests >= 0),
    CHECK (used_requests <= max_requests)
);

INSERT INTO llm_request_budget (
    id, max_requests, used_requests
)
VALUES (1, 5, 0);
