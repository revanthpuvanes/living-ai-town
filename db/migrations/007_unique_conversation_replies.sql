-- Each opening conversation event can have at most one reply.
-- Existing automatic pair/day uniqueness remains unchanged.

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_conversation_reply_parent
ON events ((payload->>'reply_to_event_id'))
WHERE type = 'CONVERSATION_SPOKEN'
  AND payload ? 'reply_to_event_id';
