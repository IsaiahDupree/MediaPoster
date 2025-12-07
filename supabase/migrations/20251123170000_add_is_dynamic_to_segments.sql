-- Add is_dynamic column to segments table if it doesn't exist

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'segments' AND column_name = 'is_dynamic') THEN
        ALTER TABLE segments ADD COLUMN is_dynamic boolean NOT NULL DEFAULT false;
    END IF;
END $$;
