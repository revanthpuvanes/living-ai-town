ALTER TABLE decisions
ADD COLUMN IF NOT EXISTS action_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_decisions_action_id
ON decisions(action_id)
WHERE action_id IS NOT NULL;
