-- Add workspace_id to people and segments tables
-- Migration: 010_add_workspace_to_people
-- Created: 2025-11-27

-- Add workspace_id to people table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'people' AND column_name = 'workspace_id'
    ) THEN
        -- Add the column
        ALTER TABLE people ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
        
        -- Set a default workspace for existing rows
        UPDATE people 
        SET workspace_id = (SELECT id FROM workspaces ORDER BY created_at LIMIT 1)
        WHERE workspace_id IS NULL;
        
        -- Make it NOT NULL after setting defaults
        ALTER TABLE people ALTER COLUMN workspace_id SET NOT NULL;
        
        -- Add index
        CREATE INDEX idx_people_workspace ON people(workspace_id);
    END IF;
END $$;

-- Add workspace_id to segments table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'segments' AND column_name = 'workspace_id'
    ) THEN
        -- Add the column
        ALTER TABLE segments ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
        
        -- Set a default workspace for existing rows
        UPDATE segments 
        SET workspace_id = (SELECT id FROM workspaces ORDER BY created_at LIMIT 1)
        WHERE workspace_id IS NULL;
        
        -- Make it NOT NULL after setting defaults
        ALTER TABLE segments ALTER COLUMN workspace_id SET NOT NULL;
        
        -- Add index
        CREATE INDEX idx_segments_workspace ON segments(workspace_id);
    END IF;
END $$;

COMMENT ON COLUMN people.workspace_id IS 'Workspace this person belongs to';
COMMENT ON COLUMN segments.workspace_id IS 'Workspace this segment belongs to';
