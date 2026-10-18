# Database Migration Guide

## Migration Files Created

✅ **001_people_graph.sql** - People Graph tables (7.7 KB)
- `people` - Core person entities
- `identities` - Cross-platform identities
- `person_events` - Unified event stream
- `person_insights` - Computed person lens
- `segments` + `segment_members` - Dynamic grouping
- `segment_insights` - Per-segment analytics
- `outbound_messages` - Email/DM tracking

✅ **002_content_graph_extensions.sql** - Content Graph additions (2.8 KB)
- `content_rollups` - Aggregated cross-platform metrics
- `content_experiments` - A/B testing framework
- Adds `traffic_type` column to existing `content_metrics` table

✅ **003_connectors.sql** - Connector configuration (2.2 KB)
- `ig_connections` - Instagram/Meta OAuth tokens
- `connector_configs` - Generic connector configuration

## How to Apply Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Open Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Go to **SQL Editor**
4. Create a new query
5. Copy/paste the contents of each migration file in order:
   - First: `001_people_graph.sql`
   - Second: `002_content_graph_extensions.sql`
   - Third: `003_connectors.sql`
6. Run each query
7. Verify tables created in **Table Editor**

### Option 2: Supabase CLI

```bash
# Install Supabase CLI if not installed
brew install supabase/tap/supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref <your-project-ref>

# Apply migrations
supabase db push

# Or run specific migration
psql $DATABASE_URL < Backend/database/migrations/001_people_graph.sql
psql $DATABASE_URL < Backend/database/migrations/002_content_graph_extensions.sql
psql $DATABASE_URL < Backend/database/migrations/003_connectors.sql
```

### Option 3: Python Script (Automated)

```bash
cd Backend
python3 -m scripts.apply_migrations
```

## Verification Steps

After applying migrations, verify with:

```sql
-- Check all new tables exist
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
  'people', 'identities', 'person_events', 'person_insights',
  'segments', 'segment_members', 'segment_insights', 'outbound_messages',
  'content_rollups', 'content_experiments',
  'ig_connections', 'connector_configs'
)
ORDER BY tablename;

-- Verify indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename LIKE 'person%' OR tablename LIKE 'segment%' OR tablename LIKE 'content%'
ORDER BY tablename, indexname;

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables  
WHERE schemaname = 'public'
AND rowsecurity = true;
```

Expected result: 12 tables, 30+ indexes, RLS enabled on all tables.

## Rollback (if needed)

```sql
-- Drop in reverse order to respect foreign keys
DROP TABLE IF EXISTS outbound_messages CASCADE;
DROP TABLE IF EXISTS segment_insights CASCADE;
DROP TABLE IF EXISTS segment_members CASCADE;
DROP TABLE IF EXISTS segments CASCADE;
DROP TABLE IF NOT EXISTS person_insights CASCADE;
DROP TABLE IF EXISTS person_events CASCADE;
DROP TABLE IF EXISTS identities CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS content_experiments CASCADE;
DROP TABLE IF EXISTS content_rollups CASCADE;
DROP TABLE IF EXISTS connector_configs CASCADE;
DROP TABLE IF EXISTS ig_connections CASCADE;
```

## Next Steps After Migration

1. ✅ Verify tables created
2. Update SQLAlchemy models (`Backend/database/models.py`)
3. Test database connection
4. Start Phase 2: Source Adapter Pattern

## Notes

- All tables have RLS enabled for security
- Indexes optimized for common query patterns
- JSONB fields for flexible metadata
- Foreign keys cascade on delete
- Traffic type separation (organic/paid) throughout
