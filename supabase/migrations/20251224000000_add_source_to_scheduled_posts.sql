-- Add source column to scheduled_posts to track where post was created from
-- Values: 'manual', 'narrative_builder', 'automation', 'experiments'

-- Add source column if it doesn't exist
ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';

-- Add index for filtering by source
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_source ON scheduled_posts(source);

-- Add comment for documentation
COMMENT ON COLUMN scheduled_posts.source IS 'Source of the scheduled post: manual, narrative_builder, automation, experiments';

-- Note: Future migrations can update existing posts based on other tables/columns
-- when those relationships are established (e.g., experiment_id, narrative_goal_id)
