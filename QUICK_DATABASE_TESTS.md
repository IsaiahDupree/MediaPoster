# 🧪 Quick Database Tests

Run these queries to verify your schema is working correctly.

---

## ✅ Test 1: Basic Health Check

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  'Total Tables' as metric, 
  COUNT(*)::text as value 
FROM pg_tables 
WHERE schemaname = 'public'
UNION ALL
SELECT 'Video Tables', COUNT(*)::text 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'video%'
UNION ALL
SELECT 'Workspaces', COUNT(*)::text FROM workspaces
UNION ALL
SELECT 'Users', COUNT(*)::text FROM users
UNION ALL
SELECT 'Videos', COUNT(*)::text FROM videos;
"
```

**Expected Output:**
```
Total Tables    | 54
Video Tables    | 11
Workspaces      | 0 (or your count)
Users           | 0 (or your count)
Videos          | [your count]
```

---

## ✅ Test 2: Check Key Table Structures

### video_words
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "\d video_words"
```

**Should show:**
- `word`, `start_s`, `end_s` columns
- `is_emphasis`, `is_cta_keyword` flags
- `sentiment_score`, `emotion` fields

### viral_patterns
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "\d viral_patterns"
```

**Should show:**
- `pattern_name`, `pattern_type`
- `avg_fate_score`, `avg_retention_3s`
- `components` JSONB field
- `confidence_score`

### clip_styles
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "\d clip_styles"
```

**Should show:**
- Caption styling fields
- Headline overlay fields
- Platform-specific settings

---

## ✅ Test 3: Create Test Workspace

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO workspaces (name, plan, settings) 
VALUES ('Test Workspace', 'free', '{}') 
RETURNING id, name, plan, created_at;
"
```

**Should return:**
- A new UUID
- 'Test Workspace'
- 'free'
- Timestamp

**Save the workspace ID for next tests!**

---

## ✅ Test 4: Create Test User

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO users (email, name) 
VALUES ('test@mediaposter.com', 'Test User') 
RETURNING id, email, name, created_at;
"
```

---

## ✅ Test 5: Link User to Workspace

Replace `<workspace_id>` and `<user_id>` with the IDs from above:

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO workspace_members (workspace_id, user_id, role) 
VALUES ('<workspace_id>', '<user_id>', 'owner') 
RETURNING workspace_id, user_id, role, joined_at;
"
```

---

## ✅ Test 6: Link Existing Videos to Workspace

Get your workspace ID first:
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT id, name FROM workspaces ORDER BY created_at DESC LIMIT 1;
"
```

Then update videos (replace `<workspace_id>`):
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
UPDATE videos 
SET workspace_id = '<workspace_id>' 
WHERE workspace_id IS NULL 
RETURNING id, file_name, workspace_id;
"
```

---

## ✅ Test 7: Create a Test Viral Pattern

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO viral_patterns (
  pattern_name, 
  pattern_type, 
  components, 
  avg_fate_score, 
  avg_retention_3s,
  video_count,
  confidence_score
) 
VALUES (
  'Pain Hook + Quick Win',
  'hook_formula',
  '{
    \"hook_type\": \"pain\",
    \"structure\": [\"problem\", \"agitation\", \"solution_tease\"],
    \"avg_hook_duration_s\": 3.5,
    \"typical_words\": [\"struggling\", \"frustrated\", \"here is how\"]
  }'::jsonb,
  0.82,
  0.91,
  15,
  0.88
) 
RETURNING id, pattern_name, pattern_type, avg_fate_score;
"
```

---

## ✅ Test 8: Query Pattern Library

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  pattern_name,
  pattern_type,
  avg_fate_score,
  avg_retention_3s,
  video_count,
  confidence_score
FROM viral_patterns
ORDER BY avg_fate_score DESC;
"
```

---

## ✅ Test 9: Check Views

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT * FROM top_viral_patterns LIMIT 5;
"
```

---

## ✅ Test 10: Insert Test Word Data

First get a video ID:
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT id, file_name FROM videos LIMIT 1;
"
```

Then insert test words (replace `<video_id>`):
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO video_words (video_id, word_index, word, start_s, end_s, is_emphasis, speech_function)
VALUES 
  ('<video_id>', 0, 'Hey', 0.0, 0.3, true, 'greeting'),
  ('<video_id>', 1, 'struggling', 0.3, 0.8, true, 'pain_point'),
  ('<video_id>', 2, 'with', 0.8, 1.0, false, null),
  ('<video_id>', 3, 'Notion', 1.0, 1.4, true, 'topic'),
  ('<video_id>', 4, 'Here', 1.4, 1.6, false, null),
  ('<video_id>', 5, 'is', 1.6, 1.7, false, null),
  ('<video_id>', 6, 'how', 1.7, 1.9, true, 'cta_intro')
RETURNING word_index, word, start_s, end_s, is_emphasis;
"
```

---

## ✅ Test 11: Query Timeline

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  word_index,
  word,
  start_s,
  end_s,
  is_emphasis,
  is_cta_keyword,
  speech_function
FROM video_words
WHERE video_id = '<video_id>'
ORDER BY word_index
LIMIT 20;
"
```

---

## ✅ Test 12: Social Account Connection

Replace `<workspace_id>`:
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
INSERT INTO social_accounts (
  workspace_id,
  platform,
  handle,
  display_name,
  status
)
VALUES (
  '<workspace_id>',
  'tiktok',
  '@testcreator',
  'Test Creator',
  'connected'
)
RETURNING id, platform, handle, status;
"
```

---

## 🔍 Useful Inspection Queries

### See All Tables
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "\dt"
```

### See All Views
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "\dv"
```

### See Table Row Counts
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  schemaname,
  tablename,
  n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC
LIMIT 20;
"
```

### See Foreign Keys
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
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
  AND tc.table_name LIKE 'video%'
ORDER BY tc.table_name;
"
```

---

## 🧹 Cleanup Test Data

If you want to remove test data:

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
DELETE FROM workspace_members WHERE user_id IN (SELECT id FROM users WHERE email = 'test@mediaposter.com');
DELETE FROM users WHERE email = 'test@mediaposter.com';
DELETE FROM workspaces WHERE name = 'Test Workspace';
DELETE FROM viral_patterns WHERE pattern_name = 'Pain Hook + Quick Win';
"
```

---

## 📊 Success Checklist

After running these tests, you should have verified:

- ✅ 54 total tables exist
- ✅ 11 video analysis tables exist  
- ✅ `video_words` table structure is correct
- ✅ `viral_patterns` table structure is correct
- ✅ Can create workspaces
- ✅ Can create users
- ✅ Can link users to workspaces
- ✅ Can link videos to workspaces
- ✅ Can insert viral patterns
- ✅ Can insert word-level data
- ✅ Can query timeline data
- ✅ Can create social account connections

---

**All tests passing? You're ready to start building services! 🚀**
