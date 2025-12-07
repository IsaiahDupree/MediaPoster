# Applying Migrations to Local Supabase

This guide shows how to apply all database migrations to your locally hosted Supabase instance.

## Option 1: Using Supabase CLI (Recommended)

If you're using Supabase CLI for local development:

```bash
# Navigate to your project root (where supabase/ folder is)
cd /Users/isaiahdupree/Documents/Software/MediaPoster

# Reset and apply all migrations
supabase db reset

# Or if you have migrations in supabase/migrations folder:
supabase migration up
```

## Option 2: Using psql Directly

If you have a local PostgreSQL instance or direct connection:

```bash
# Set your database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Or for local Supabase:
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# Run the Python script
cd Backend/database/migrations
python3 apply_all_migrations.py

# Or use the bash script
./apply_all_migrations.sh
```

## Option 3: Manual Application

Apply migrations one by one in order:

```bash
cd Backend/database/migrations

psql $DATABASE_URL -f 000_content_base_tables.sql
psql $DATABASE_URL -f 001_people_graph.sql
psql $DATABASE_URL -f 002_content_graph_extensions.sql
psql $DATABASE_URL -f 003_connectors.sql
psql $DATABASE_URL -f 003_base_video_tables.sql
psql $DATABASE_URL -f 004_content_intelligence_video_analysis.sql
psql $DATABASE_URL -f 005_content_intelligence_platform_tracking.sql
psql $DATABASE_URL -f 006_content_intelligence_insights_metrics.sql
psql $DATABASE_URL -f 008_video_library.sql
psql $DATABASE_URL -f 009_fix_video_library_fk.sql
psql $DATABASE_URL -f 009_video_thumbnails.sql
psql $DATABASE_URL -f 005_video_clips.sql
psql $DATABASE_URL -f 006_segment_editing.sql
psql $DATABASE_URL -f 007_publishing_queue.sql
```

## Migration Order

The migrations are applied in this order to respect dependencies:

1. **000_content_base_tables.sql** - Base content tables (content_items, content_variants, content_metrics)
2. **001_people_graph.sql** - People Graph tables
3. **002_content_graph_extensions.sql** - Content rollups and experiments
4. **003_connectors.sql** - Connector configuration
5. **003_base_video_tables.sql** - Original videos and clips
6. **004_content_intelligence_video_analysis.sql** - Video analysis tables
7. **005_content_intelligence_platform_tracking.sql** - Platform tracking
8. **006_content_intelligence_insights_metrics.sql** - Insights and metrics
9. **008_video_library.sql** - Video library (references content_items)
10. **009_fix_video_library_fk.sql** - Fix FK constraint
11. **009_video_thumbnails.sql** - Add thumbnail support
12. **005_video_clips.sql** - Video clips (references videos)
13. **006_segment_editing.sql** - Segment editing (references video_segments)
14. **007_publishing_queue.sql** - Publishing queue (references content_items, video_clips)

## Verification

After applying migrations, verify with:

```sql
-- Check key tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
  'content_items', 'content_variants', 'content_metrics',
  'people', 'identities', 'person_events',
  'videos', 'video_analysis', 'video_clips',
  'platform_posts', 'platform_checkbacks'
)
ORDER BY table_name;

-- Check migration history (if using Supabase CLI)
SELECT * FROM supabase_migrations.schema_migrations 
ORDER BY version;
```

## Troubleshooting

### Error: "relation already exists"
- Some tables may already exist. The migrations use `CREATE TABLE IF NOT EXISTS`, so this is usually safe to ignore.

### Error: "foreign key constraint"
- Make sure migrations are applied in order
- Check that dependent tables exist first

### Error: "permission denied"
- Make sure your database user has CREATE privileges
- For local Supabase, use the default postgres user

### Error: "psql: command not found"
- Install PostgreSQL client: `brew install postgresql` (macOS)
- Or use Supabase CLI instead

## Notes

- All migrations use `IF NOT EXISTS` where possible to be idempotent
- Foreign keys are set up with `ON DELETE CASCADE` or `ON DELETE SET NULL` as appropriate
- RLS is enabled on most tables (policies may need to be added based on your auth setup)


