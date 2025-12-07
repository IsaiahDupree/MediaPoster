-- 04_content_metrics_experiments.sql

-- Metrics snapshots per variant
create table if not exists content_metrics (
  id bigserial primary key,
  variant_id uuid not null references content_variants(id) on delete cascade,
  snapshot_at timestamptz not null,

  traffic_type text not null check (traffic_type in ('organic','paid')),

  views bigint,
  impressions bigint,
  reach bigint,
  likes bigint,
  comments bigint,
  shares bigint,
  saves bigint,
  clicks bigint,
  watch_time_seconds bigint,

  sentiment_score numeric,        -- -1..1 avg sentiment at this snapshot
  metadata jsonb,

  created_at timestamptz not null default now()
);

create index if not exists idx_content_metrics_variant_time
  on content_metrics (variant_id, snapshot_at desc);


-- Rollups per canonical content item (aggregated periodically)
create table if not exists content_rollups (
  content_id uuid primary key references content_items(id) on delete cascade,

  total_views_organic bigint,
  total_views_paid bigint,
  total_impressions_organic bigint,
  total_impressions_paid bigint,
  total_likes_organic bigint,
  total_likes_paid bigint,
  total_comments_organic bigint,
  total_comments_paid bigint,
  total_shares_organic bigint,
  total_shares_paid bigint,
  total_saves_organic bigint,
  total_saves_paid bigint,
  total_clicks_organic bigint,
  total_clicks_paid bigint,

  avg_watch_time_seconds_organic numeric,
  avg_watch_time_seconds_paid numeric,

  global_sentiment numeric,       -- overall weighted sentiment
  best_platform text,             -- computed from your scoring logic

  last_updated_at timestamptz not null default now()
);


-- Cross-platform experiments (A/B / APINK)
create table if not exists content_experiments (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references content_items(id) on delete cascade,
  name text not null,
  hypothesis text,
  primary_metric text,            -- "click_through_rate", "watch_time", etc.
  created_by uuid,
  created_at timestamptz not null default now()
);

create index if not exists idx_content_experiments_content
  on content_experiments (content_id);
