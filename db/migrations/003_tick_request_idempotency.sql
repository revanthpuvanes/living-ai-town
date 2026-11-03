-- A logical tick request has a stable UUID.
-- Existing historical ticks can have NULL request IDs.

ALTER TABLE ticks
ADD COLUMN IF NOT EXISTS request_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS
    ticks_request_id_unique
ON ticks (request_id)
WHERE request_id IS NOT NULL;
