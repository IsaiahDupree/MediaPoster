-- 20251125000000_workspace_architecture.sql

-- 1. Create workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  description TEXT,
  settings JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);
CREATE INDEX IF NOT EXISTS idx_workspaces_deleted ON workspaces(deleted_at) WHERE deleted_at IS NULL;

-- 2. Create workspace_members table
CREATE TABLE IF NOT EXISTS workspace_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,  -- References auth.users
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  invited_by UUID,
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id);

-- 3. Create Default Workspace for migration
INSERT INTO workspaces (id, name, slug, description)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Default Workspace',
  'default',
  'Auto-created workspace for existing data'
) ON CONFLICT (id) DO NOTHING;

-- 4. Add workspace_id to core tables (Nullable first, then backfill, then NOT NULL)

-- Helper macro-like function to add workspace_id safely
DO $$
DECLARE
    default_workspace_id UUID := '00000000-0000-0000-0000-000000000001';
    tables TEXT[] := ARRAY[
        'people', 
        'segments', 
        'content_items', 
        'analyzed_videos', 
        'original_videos', 
        'ig_connections', 
        'connector_configs'
    ];
    t TEXT;
BEGIN
    FOREACH t IN ARRAY tables LOOP
        -- Add column if not exists
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'workspace_id') THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE', t);
            
            -- Backfill existing data
            EXECUTE format('UPDATE %I SET workspace_id = %L WHERE workspace_id IS NULL', t, default_workspace_id);
            
            -- Make NOT NULL
            EXECUTE format('ALTER TABLE %I ALTER COLUMN workspace_id SET NOT NULL', t);
            
            -- Add Index
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_workspace ON %I(workspace_id)', t, t);
        END IF;
    END LOOP;
END $$;

-- 5. Enable RLS on new tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- 6. Helper Functions for RLS

-- Get current user's ID (safe wrapper)
CREATE OR REPLACE FUNCTION public.safe_user_id()
RETURNS UUID AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid;
$$ LANGUAGE SQL STABLE;

-- Get user's workspaces
CREATE OR REPLACE FUNCTION user_workspaces()
RETURNS SETOF UUID AS $$
  SELECT workspace_id FROM workspace_members
  WHERE user_id = public.safe_user_id();
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- 7. RLS Policies

-- Workspaces
DROP POLICY IF EXISTS "Users can view their workspaces" ON workspaces;
CREATE POLICY "Users can view their workspaces"
  ON workspaces FOR SELECT
  TO authenticated
  USING (id IN (SELECT user_workspaces()));

DROP POLICY IF EXISTS "Users can create workspaces" ON workspaces;
CREATE POLICY "Users can create workspaces"
  ON workspaces FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Workspace Members
DROP POLICY IF EXISTS "Users can view workspace members in their workspaces" ON workspace_members;
CREATE POLICY "Users can view workspace members in their workspaces"
  ON workspace_members FOR SELECT
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()));

-- Update Core Table Policies (Example: People)
-- Note: We need to drop the old "allow all" policies first
DROP POLICY IF EXISTS "Allow all access for authenticated users" ON people;

CREATE POLICY "Users can view people in their workspaces"
  ON people FOR SELECT
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can insert people in their workspaces"
  ON people FOR INSERT
  TO authenticated
  WITH CHECK (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can update people in their workspaces"
  ON people FOR UPDATE
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()))
  WITH CHECK (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can delete people in their workspaces"
  ON people FOR DELETE
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()));

-- Repeat for other tables (simplified for this migration script, ideally done per table)
-- For now, we'll apply the same pattern to content_items as a critical example
DROP POLICY IF EXISTS "Allow all access for authenticated users" ON content_items;

CREATE POLICY "Users can view content_items in their workspaces"
  ON content_items FOR SELECT
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can insert content_items in their workspaces"
  ON content_items FOR INSERT
  TO authenticated
  WITH CHECK (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can update content_items in their workspaces"
  ON content_items FOR UPDATE
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()))
  WITH CHECK (workspace_id IN (SELECT user_workspaces()));

CREATE POLICY "Users can delete content_items in their workspaces"
  ON content_items FOR DELETE
  TO authenticated
  USING (workspace_id IN (SELECT user_workspaces()));
