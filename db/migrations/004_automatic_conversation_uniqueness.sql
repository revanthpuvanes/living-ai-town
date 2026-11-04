-- Automatic conversation events carry a stable daily pair key.
-- Manual conversations do not carry this field.
--
-- PostgreSQL enforces one automatic conversation per pair/day,
-- regardless of speaker order or concurrent workers.

CREATE UNIQUE INDEX idx_auto_conversation_pair_day
ON events ((payload->>'auto_pair_day'))
WHERE type = 'CONVERSATION_SPOKEN'
  AND payload ? 'auto_pair_day';
