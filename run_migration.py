import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("Backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

async def run_migration():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        try:
            # Read the migration file content
            with open('supabase/migrations/20251125000000_workspace_architecture.sql', 'r') as f:
                sql_content = f.read()
            
            # Split by statement separator (;) but handle the DO $$ block carefully
            # A simple split by ';' might break the DO block.
            # Let's execute the critical parts sequentially manually for safety in this script
            
            statements = [
                # 0. Reset for development (Optional, but helps with the error)
                "DROP TABLE IF EXISTS workspace_members CASCADE;",
                "DROP TABLE IF EXISTS workspaces CASCADE;",

                # 1. Create workspaces table
                """
                CREATE TABLE workspaces (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                  name TEXT NOT NULL,
                  slug TEXT UNIQUE NOT NULL,
                  description TEXT,
                  settings JSONB DEFAULT '{}'::jsonb,
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  updated_at TIMESTAMPTZ DEFAULT NOW(),
                  deleted_at TIMESTAMPTZ
                );
                """,
                "CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);",
                "CREATE INDEX IF NOT EXISTS idx_workspaces_deleted ON workspaces(deleted_at) WHERE deleted_at IS NULL;",
                
                # 2. Create workspace_members table
                """
                CREATE TABLE IF NOT EXISTS workspace_members (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                  user_id UUID NOT NULL,
                  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
                  invited_by UUID,
                  joined_at TIMESTAMPTZ DEFAULT NOW(),
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  UNIQUE(workspace_id, user_id)
                );
                """,
                "CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id);",
                
                # 3. Create Default Workspace
                """
                INSERT INTO workspaces (id, name, slug, description)
                VALUES (
                  '00000000-0000-0000-0000-000000000001',
                  'Default Workspace',
                  'default',
                  'Auto-created workspace for existing data'
                ) ON CONFLICT (id) DO NOTHING;
                """,
                
                # 4. Add workspace_id to core tables (DO block)
                """
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
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'workspace_id') THEN
                            EXECUTE format('ALTER TABLE %I ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE', t);
                            EXECUTE format('UPDATE %I SET workspace_id = %L WHERE workspace_id IS NULL', t, default_workspace_id);
                            EXECUTE format('ALTER TABLE %I ALTER COLUMN workspace_id SET NOT NULL', t);
                            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_workspace ON %I(workspace_id)', t, t);
                        END IF;
                    END LOOP;
                END $$;
                """,
                
                # 5. Enable RLS
                "ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;",
                
                # 6. Helper Functions
                """
                CREATE OR REPLACE FUNCTION public.safe_user_id()
                RETURNS UUID AS $$
                  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid;
                $$ LANGUAGE SQL STABLE;
                """,
                """
                CREATE OR REPLACE FUNCTION user_workspaces()
                RETURNS SETOF UUID AS $$
                  SELECT workspace_id FROM workspace_members
                  WHERE user_id = public.safe_user_id();
                $$ LANGUAGE SQL STABLE SECURITY DEFINER;
                """,
                
                # 7. RLS Policies
                "DROP POLICY IF EXISTS \"Users can view their workspaces\" ON workspaces;",
                """
                CREATE POLICY "Users can view their workspaces"
                  ON workspaces FOR SELECT
                  TO authenticated
                  USING (id IN (SELECT user_workspaces()));
                """,
                "DROP POLICY IF EXISTS \"Users can create workspaces\" ON workspaces;",
                """
                CREATE POLICY "Users can create workspaces"
                  ON workspaces FOR INSERT
                  TO authenticated
                  WITH CHECK (true);
                """,
                "DROP POLICY IF EXISTS \"Users can view workspace members in their workspaces\" ON workspace_members;",
                """
                CREATE POLICY "Users can view workspace members in their workspaces"
                  ON workspace_members FOR SELECT
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()));
                """,
                
                # Core Table Policies (People)
                "DROP POLICY IF EXISTS \"Allow all access for authenticated users\" ON people;",
                """
                CREATE POLICY "Users can view people in their workspaces"
                  ON people FOR SELECT
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can insert people in their workspaces"
                  ON people FOR INSERT
                  TO authenticated
                  WITH CHECK (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can update people in their workspaces"
                  ON people FOR UPDATE
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()))
                  WITH CHECK (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can delete people in their workspaces"
                  ON people FOR DELETE
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()));
                """,
                
                # Core Table Policies (Content Items)
                "DROP POLICY IF EXISTS \"Allow all access for authenticated users\" ON content_items;",
                """
                CREATE POLICY "Users can view content_items in their workspaces"
                  ON content_items FOR SELECT
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can insert content_items in their workspaces"
                  ON content_items FOR INSERT
                  TO authenticated
                  WITH CHECK (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can update content_items in their workspaces"
                  ON content_items FOR UPDATE
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()))
                  WITH CHECK (workspace_id IN (SELECT user_workspaces()));
                """,
                """
                CREATE POLICY "Users can delete content_items in their workspaces"
                  ON content_items FOR DELETE
                  TO authenticated
                  USING (workspace_id IN (SELECT user_workspaces()));
                """
            ]

            for stmt in statements:
                if stmt.strip():
                    print(f"Executing: {stmt[:50]}...")
                    await conn.execute(text(stmt))
            
            print("Migration successful")
        except Exception as e:
            print("Migration failed:", e)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
