# EverReach/Blend: Comprehensive Database Schema

## People Graph (EverReach Core)

### `people`
Core person entity - one row per unique human.

```sql
CREATE TABLE people (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT,
  primary_email TEXT,
  company TEXT,
  role TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `identities`
All the ways we see a person across platforms.

```sql
CREATE TABLE identities (
  id BIGSERIAL PRIMARY KEY,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  channel TEXT CHECK (channel IN ('email','instagram','linkedin','twitter','facebook','tiktok','youtube','threads','bluesky','pinterest')),
  handle TEXT NOT NULL,          -- @user, linkedin url, page-scoped id
  extra JSONB,                   -- profile_pic, bio, location, follower_count
  is_verified BOOLEAN DEFAULT FALSE,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(channel, handle)
);

CREATE INDEX idx_identities_person ON identities(person_id);
CREATE INDEX idx_identities_channel ON identities(channel);
```

### `person_events`
Unified event stream of all interactions.

```sql
CREATE TABLE person_events (
  id BIGSERIAL PRIMARY KEY,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,         -- email / instagram / linkedin / twitter / facebook / site
  event_type TEXT NOT NULL,      -- opened_email, clicked_link, commented, liked, dm_sent, dm_reply, shared, saved
  platform_id TEXT,              -- post id / email id / message id
  content_excerpt TEXT,
  sentiment NUMERIC CHECK (sentiment >= -1 AND sentiment <= 1),
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')) DEFAULT 'organic',
  metadata JSONB,
  occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_person_events_person ON person_events(person_id, occurred_at DESC);
CREATE INDEX idx_person_events_type ON person_events(event_type, occurred_at DESC);
CREATE INDEX idx_person_events_traffic ON person_events(traffic_type);
```

### `person_insights`
Computed "lens" for each person.

```sql
CREATE TABLE person_insights (
  person_id UUID PRIMARY KEY REFERENCES people(id) ON DELETE CASCADE,
  interests JSONB,               -- ["3D printing","AI automation","email marketing"]
  tone_preferences JSONB,        -- ["playful","technical","short-form"]
  channel_preferences JSONB,     -- {"email":0.9,"instagram_dm":0.7,"linkedin":0.4}
  avg_reply_time INTERVAL,
  activity_state TEXT CHECK (activity_state IN ('active','warming','cool','dormant')),
  last_active_at TIMESTAMPTZ,
  seasonality JSONB,             -- per month/weekday performance histograms
  warmth_score NUMERIC,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `segments`
Dynamic groups of people.

```sql
CREATE TABLE segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  definition JSONB,              -- query/DSL for segment membership
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE segment_members (
  segment_id UUID REFERENCES segments(id) ON DELETE CASCADE,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (segment_id, person_id)
);

CREATE INDEX idx_segment_members_person ON segment_members(person_id);
```

### `segment_insights`
Per-segment analytics (organic vs paid separated).

```sql
CREATE TABLE segment_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  segment_id UUID REFERENCES segments(id) ON DELETE CASCADE,
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')),
  top_topics JSONB,
  top_platforms JSONB,           -- {"instagram": 0.7, "twitter":0.2, "linkedin":0.1}
  top_formats JSONB,             -- {"reels":0.6,"carousels":0.3,"threads":0.1}
  engagement_style JSONB,        -- {"saves":0.5,"comments":0.3,"shares":0.2}
  best_times JSONB,              -- {"Tue_11_14":0.8,...}
  expected_reach_range INT4RANGE,
  expected_engagement_rate_range NUMRANGE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(segment_id, traffic_type)
);
```

### `outbound_messages`
Log of all emails/DMs sent.

```sql
CREATE TABLE outbound_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES segments(id) ON DELETE SET NULL,
  channel TEXT NOT NULL,
  goal_type TEXT,                -- nurture / offer / reactivation / etc.
  variant TEXT,                  -- A, B, C
  subject TEXT,
  body TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  metadata JSONB
);

CREATE INDEX idx_outbound_person ON outbound_messages(person_id, sent_at DESC);
CREATE INDEX idx_outbound_segment ON outbound_messages(segment_id, sent_at DESC);
```

---

## Content Graph (Blend Cross-Platform)

### `content_items`
Canonical content pieces - the single source of truth.

```sql
CREATE TABLE content_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE,
  type TEXT CHECK (type IN ('video','article','audio','image','carousel')),
  source_url TEXT,               -- your on-site or storage URL
  title TEXT,
  description TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_items_created ON content_items(created_at DESC);
CREATE INDEX idx_content_items_creator ON content_items(created_by);
```

### `content_variants`
Platform-specific executions of content.

```sql
CREATE TABLE content_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
  platform TEXT CHECK (platform IN (
    'instagram','tiktok','youtube','linkedin','twitter','facebook',
    'pinterest','threads','bluesky','other'
  )),
  platform_post_id TEXT,         -- id returned by platform or Blotato
  platform_post_url TEXT,
  title TEXT,
  description TEXT,
  thumbnail_url TEXT,
  scheduled_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  is_paid BOOLEAN DEFAULT FALSE,
  experiment_id UUID,
  variant_label TEXT,            -- "Title A / Thumb 1"
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_variants_content ON content_variants(content_id);
CREATE INDEX idx_variants_platform ON content_variants(platform, published_at DESC);
CREATE INDEX idx_variants_experiment ON content_variants(experiment_id);
```

### `content_metrics`
Time-series performance snapshots.

```sql
CREATE TABLE content_metrics (
  id BIGSERIAL PRIMARY KEY,
  variant_id UUID REFERENCES content_variants(id) ON DELETE CASCADE,
  snapshot_at TIMESTAMPTZ DEFAULT NOW(),
  views BIGINT,
  impressions BIGINT,
  reach BIGINT,
  likes BIGINT,
  comments BIGINT,
  shares BIGINT,
  saves BIGINT,
  clicks BIGINT,
  watch_time_seconds BIGINT,
  sentiment_score NUMERIC CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')) DEFAULT 'organic',
  metadata JSONB
);

CREATE INDEX idx_metrics_variant ON content_metrics(variant_id, snapshot_at DESC);
CREATE INDEX idx_metrics_traffic ON content_metrics(traffic_type);
```

### `content_rollups`
Nightly aggregated metrics per content ID.

```sql
CREATE TABLE content_rollups (
  content_id UUID PRIMARY KEY REFERENCES content_items(id) ON DELETE CASCADE,
  total_views BIGINT,
  total_impressions BIGINT,
  total_likes BIGINT,
  total_comments BIGINT,
  total_shares BIGINT,
  total_saves BIGINT,
  total_clicks BIGINT,
  avg_watch_time_seconds NUMERIC,
  global_sentiment NUMERIC,
  best_platform TEXT,
  last_updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `content_experiments`
A/B/multivariate testing framework.

```sql
CREATE TABLE content_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  hypothesis TEXT,
  primary_metric TEXT,           -- "click_through_rate", "watch_time", etc.
  status TEXT CHECK (status IN ('draft','running','completed','cancelled')) DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);
```

---

## Platform Connectors

### `ig_connections`
Instagram/Meta OAuth connections.

```sql
CREATE TABLE ig_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  everreach_user_id UUID NOT NULL,
  fb_page_id TEXT NOT NULL,
  ig_business_id TEXT NOT NULL,
  access_token TEXT NOT NULL,
  token_expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ
);

CREATE INDEX idx_ig_conn_user ON ig_connections(everreach_user_id);
```

### `connector_configs`
Generic connector configuration store.

```sql
CREATE TABLE connector_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  connector_type TEXT NOT NULL, -- 'meta', 'youtube', 'tiktok', 'blotato', 'linkedin', 'twitter'
  config JSONB NOT NULL,        -- API keys, OAuth tokens, secrets
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, connector_type)
);
```

---

## Indexes & Constraints

```sql
-- Composite indexes for common queries
CREATE INDEX idx_events_channel_occurred ON person_events(channel, occurred_at DESC);
CREATE INDEX idx_events_person_channel ON person_events(person_id, channel, occurred_at DESC);

-- Full-text search on content
CREATE INDEX idx_content_title_search ON content_items USING GIN (to_tsvector('english', title));
CREATE INDEX idx_content_desc_search ON content_items USING GIN (to_tsvector('english', description));

-- Partial indexes for active data
CREATE INDEX idx_active_people ON person_insights(person_id) WHERE activity_state IN ('active','warming');
CREATE INDEX idx_scheduled_variants ON content_variants(scheduled_at) WHERE published_at IS NULL;
```
