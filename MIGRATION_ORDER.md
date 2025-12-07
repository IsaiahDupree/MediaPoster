# 🚀 Migration Execution Order

## Overview
Execute these migrations in order to build your complete MediaPoster system.

---

## Migration Sequence

### **Step 1: Phase 1 Essentials** ⚡ START HERE
**File**: `Backend/migrations/phase_1_essentials.sql`

**What it adds**:
- ✅ Workspaces & multi-tenant foundation
- ✅ Users & workspace members
- ✅ Social accounts (connected platforms)
- ✅ Content items (canonical content)
- ✅ Videos enhancement (adds workspace_id, content_item_id)
- ✅ Clips (time ranges from videos)
- ✅ Clip styles (captions + headline overlays)
- ✅ Posts (scheduled/published content)
- ✅ Post platform publish (platform IDs/URLs)

**Run it**:
```bash
cat Backend/migrations/phase_1_essentials.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

**Test it**:
```sql
-- Check tables
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('workspaces', 'users', 'clips', 'posts')
ORDER BY tablename;

-- Should see: clips, posts, users, workspaces
```

---

### **Step 2: Comprehensive Viral Analysis** 🎬 RECOMMENDED NEXT
**File**: `Backend/migrations/add_comprehensive_viral_schema.sql`

**What it adds**:
- ✅ Word-level transcript analysis
- ✅ Frame-by-frame visual analysis
- ✅ Audio & voice analysis
- ✅ Copy elements (hooks, CTAs)
- ✅ Enhanced FATE model scoring
- ✅ Platform intent tracking
- ✅ Offer/monetization analysis
- ✅ Retention events
- ✅ Viral patterns library

**Run it**:
```bash
cat Backend/migrations/add_comprehensive_viral_schema.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

**Test it**:
```sql
-- Check viral tables
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE 'video_%'
ORDER BY tablename;

-- Should see 10+ video_* tables
```

---

### **Step 3: Video Analysis Tables** (Optional - only if not using Step 2)
**File**: `Backend/migrations/add_video_analysis_tables.sql`

**What it adds**:
- ✅ Basic video_analysis table
- ✅ Basic video_segments table
- ✅ Video predictions

**Note**: This is the **simpler version**. If you ran Step 2, **skip this**.

---

### **Step 4: Publishing & Metrics** (Coming Soon)
**File**: `Backend/migrations/add_publishing_metrics.sql` (to be created)

**What it will add**:
- Post checkbacks (1h, 6h, 24h, 7d metrics)
- Post comments with sentiment
- Metric rollups (NSMs)
- Insights & recommendations

---

### **Step 5: People Graph (EverReach CRM)** (Optional - Advanced)
**File**: `Backend/migrations/add_people_graph.sql` (to be created)

**What it will add**:
- People (audience members)
- Identities (social handles per person)
- Person events (interactions)
- Person insights (AI analysis)
- Segments & segment members
- Outbound messages

**When to use**: If you want full CRM capabilities with audience tracking.

---

## Quick Start: Minimal Setup

**Just want to get started with viral analysis?**

Run these **2 migrations only**:

```bash
# 1. Foundation
cat Backend/migrations/phase_1_essentials.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres

# 2. Viral Analysis
cat Backend/migrations/add_comprehensive_viral_schema.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

**Done!** You now have:
- ✅ Multi-tenant workspaces
- ✅ Clip creation & styling
- ✅ Post scheduling
- ✅ Complete viral video analysis
- ✅ Pattern library

---

## Verification Queries

### **Check Migration Status**
```sql
-- Count tables
SELECT COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public';

-- List all tables
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### **Check Foreign Keys**
```sql
-- Verify relationships
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;
```

### **Check Views**
```sql
-- List all views
SELECT viewname
FROM pg_views
WHERE schemaname = 'public';
```

---

## Rollback (If Needed)

### **Rollback Phase 1**
```sql
DROP VIEW IF EXISTS clips_full CASCADE;
DROP VIEW IF EXISTS posts_full CASCADE;

DROP TABLE IF EXISTS post_platform_publish CASCADE;
DROP TABLE IF EXISTS posts CASCADE;
DROP TABLE IF EXISTS clip_styles CASCADE;
DROP TABLE IF EXISTS clips CASCADE;
DROP TABLE IF EXISTS content_items CASCADE;
DROP TABLE IF EXISTS social_accounts CASCADE;
DROP TABLE IF EXISTS workspace_members CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

### **Rollback Comprehensive Viral Schema**
```sql
DROP VIEW IF EXISTS videos_complete_analysis CASCADE;
DROP VIEW IF EXISTS top_viral_patterns CASCADE;

DROP TABLE IF EXISTS video_pattern_matches CASCADE;
DROP TABLE IF EXISTS viral_patterns CASCADE;
DROP TABLE IF EXISTS video_retention_events CASCADE;
DROP TABLE IF EXISTS video_offer_analysis CASCADE;
DROP TABLE IF EXISTS video_platform_intent CASCADE;
DROP TABLE IF EXISTS video_copy_elements CASCADE;
DROP TABLE IF EXISTS video_audio_analysis CASCADE;
DROP TABLE IF EXISTS video_frames CASCADE;
DROP TABLE IF EXISTS video_words CASCADE;

-- Note: Doesn't drop video_analysis or video_segments 
-- as they may have been created by the basic schema
```

---

## Migration Compatibility

### **Safe to run multiple times?**
- ✅ Phase 1: Uses `IF NOT EXISTS` - safe
- ✅ Comprehensive Viral: Uses `IF NOT EXISTS` - safe
- ⚠️ Basic Video Analysis: May conflict with comprehensive - choose one

### **Order matters?**
Yes! Always run Phase 1 first, then others.

### **Can I skip steps?**
- ✅ Can skip People Graph (Step 5) if you don't need CRM
- ✅ Can skip Publishing Metrics if you just want analysis
- ⚠️ Cannot skip Phase 1 - it's the foundation

---

## What's Next?

After running migrations:

1. **Seed test data** - Create a workspace, user, video
2. **Test API endpoints** - Ensure backend can query new tables
3. **Build services** - Word analyzer, frame analyzer, etc.
4. **Update frontend** - Add UI for new capabilities

---

## Need Help?

### **Common Issues**

**Error: "relation does not exist"**
→ Run Phase 1 first

**Error: "column already exists"**
→ That's OK! Migration is idempotent

**Error: "foreign key constraint fails"**
→ Check that referenced tables exist (run Phase 1)

### **Verify Setup**
```sql
-- Quick health check
SELECT 
  (SELECT COUNT(*) FROM workspaces) as workspaces,
  (SELECT COUNT(*) FROM users) as users,
  (SELECT COUNT(*) FROM videos) as videos,
  (SELECT COUNT(*) FROM clips) as clips,
  (SELECT COUNT(*) FROM posts) as posts;
```

---

**Ready to analyze viral videos! 🎬**
