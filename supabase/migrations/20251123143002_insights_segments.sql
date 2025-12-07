-- 02_insights_segments.sql

-- Cached per-person lens
create table if not exists person_insights (
  person_id uuid primary key references people(id) on delete cascade,

  interests jsonb,                -- ["AI automation","3D printing",...]
  tone_preferences jsonb,         -- ["casual","practical"]
  channel_preferences jsonb,      -- {"email":0.9,"instagram_dm":0.7,"linkedin":0.4}
  activity_state text check (activity_state in ('active','warming','cool','dormant')),
  last_active_at timestamptz,
  seasonality jsonb,              -- histograms by day/hour/month

  warmth_score numeric,           -- 0..1 or 0..100
  last_sentiment numeric,         -- -1..1 aggregate

  updated_at timestamptz not null default now()
);


-- Segments: named buckets of people (dynamic or materialized)
create table if not exists segments (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  definition jsonb,               -- DSL / query definition (optional)
  is_dynamic boolean not null default false,
  created_by uuid,                -- user id (if needed)
  created_at timestamptz not null default now()
);


-- Segment members: materialized membership
create table if not exists segment_members (
  segment_id uuid not null references segments(id) on delete cascade,
  person_id uuid not null references people(id) on delete cascade,
  added_at timestamptz not null default now(),
  primary key (segment_id, person_id)
);

create index if not exists idx_segment_members_person
  on segment_members (person_id);


-- Segment-level insights, split by organic/paid
create table if not exists segment_insights (
  segment_id uuid not null references segments(id) on delete cascade,
  traffic_type text not null check (traffic_type in ('organic','paid')),

  top_topics jsonb,               -- ["AI automation","copywriting",...]
  top_platforms jsonb,            -- {"instagram":0.7,"twitter":0.2,"linkedin":0.1}
  top_formats jsonb,              -- {"reels":0.6,"carousels":0.3,"threads":0.1}
  engagement_style jsonb,         -- {"saves":0.5,"comments":0.3,"shares":0.2}
  best_times jsonb,               -- {"Tue_11_14":0.8,...}
  expected_reach_range int4range,
  expected_engagement_rate_range numrange,

  updated_at timestamptz not null default now(),
  primary key (segment_id, traffic_type)
);


-- Outbound messages (email, DM, etc.)
create table if not exists outbound_messages (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references people(id) on delete cascade,
  segment_id uuid references segments(id) on delete set null,
  channel text not null check (channel in ('email','instagram_dm','facebook_dm','linkedin_dm','twitter_dm','other')),
  goal_type text,                 -- invite_to_offer / nurture / reactivation / etc.
  variant text,                   -- A/B variant label
  subject text,
  body text not null,
  metadata jsonb,

  sent_at timestamptz,
  delivered_at timestamptz,
  failed_at timestamptz,
  failure_reason text,

  created_at timestamptz not null default now()
);

create index if not exists idx_outbound_messages_person
  on outbound_messages (person_id, sent_at desc);
