-- 01_core_people.sql

-- People: one row per human
create table if not exists people (
  id uuid primary key default gen_random_uuid(),
  full_name text,
  primary_email text,
  company text,
  role text,
  timezone text,
  created_at timestamptz not null default now()
);

create index if not exists idx_people_email on people (primary_email);


-- Identities: all known handles/accounts for a person
create table if not exists identities (
  id bigserial primary key,
  person_id uuid not null references people(id) on delete cascade,
  channel text not null check (channel in (
    'email',
    'instagram',
    'facebook',
    'threads',
    'twitter',
    'linkedin',
    'tiktok',
    'youtube',
    'pinterest',
    'other'
  )),
  handle text not null,           -- email, @handle, URL, platform user id
  extra jsonb,                    -- profile_pic_url, bio, location, etc.
  is_verified boolean not null default false,
  created_at timestamptz not null default now()
);

create unique index if not exists uq_identities_channel_handle
  on identities (channel, handle);


-- Person events: everything they do with you
create table if not exists person_events (
  id bigserial primary key,
  person_id uuid not null references people(id) on delete cascade,
  channel text not null check (channel in (
    'email',
    'instagram',
    'facebook',
    'threads',
    'twitter',
    'linkedin',
    'tiktok',
    'youtube',
    'website',
    'other'
  )),
  event_type text not null,       -- e.g. opened_email, clicked_link, commented, liked, dm_reply
  traffic_type text not null check (traffic_type in ('organic','paid')),
  platform_id text,               -- platform-specific id (post id, email id, message id)
  content_excerpt text,
  sentiment numeric,              -- -1..1
  metadata jsonb,                 -- raw event info or extra fields
  occurred_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_person_events_person_time
  on person_events (person_id, occurred_at desc);

create index if not exists idx_person_events_channel_type
  on person_events (channel, event_type);
