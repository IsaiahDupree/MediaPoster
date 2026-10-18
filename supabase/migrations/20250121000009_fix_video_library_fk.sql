-- Fix Video Library Foreign Key Constraint
-- Migration: 009_fix_video_library_fk
-- Removes FK constraint to auth.users to allow placeholder UUIDs
-- RLS policies will be added later when auth system is implemented

-- Drop the foreign key constraint on user_id
ALTER TABLE videos 
DROP CONSTRAINT IF EXISTS videos_user_id_fkey;

-- Note: RLS is already disabled in the original migration
-- When auth is implemented, re-enable RLS and add policies:
-- ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view their own videos" ON videos
--     FOR SELECT USING (auth.uid() = user_id);

COMMENT ON COLUMN videos.user_id IS 'User ID - FK constraint removed temporarily to allow placeholder UUIDs until auth system is implemented';

