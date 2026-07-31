-- Creator-profile memory: goals + constraints on brands, so
-- recommend_next_content can be personalized via brand_id instead of
-- needing available_minutes/goal re-passed as raw call args every time.

ALTER TABLE brands ADD COLUMN IF NOT EXISTS primary_goal TEXT;
ALTER TABLE brands ADD COLUMN IF NOT EXISTS available_minutes_per_day INTEGER;
