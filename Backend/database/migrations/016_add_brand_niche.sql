-- Add a niche field to brands so trend-detection and content recommendation
-- can be scoped to a brand's niche (e.g. "AI automation", "fitness").
-- The brands table itself predates the numbered migration files (created via
-- SQLAlchemy metadata.create_all), so this is the first migration to touch it.

ALTER TABLE brands ADD COLUMN IF NOT EXISTS niche TEXT;

CREATE INDEX IF NOT EXISTS ix_brands_niche ON brands(niche);
