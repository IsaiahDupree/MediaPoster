-- 03_content_core.sql

-- Canonical content item (global content ID)
create table if not exists content_items (
  id uuid primary key default gen_random_uuid(),
  slug text unique,
  type text not null check (type in ('video','article','audio','image','carousel','other')),
  source_url text,                -- your local/private URL or storage path
  title text,
  description text,
  created_by uuid,                -- user id
  created_at timestamptz not null default now()
);


-- Platform-specific variants
create table if not exists content_variants (
  id uuid primary key default gen_random_uuid(),
  content_id uuid not null references content_items(id) on delete cascade,

  platform text not null check (platform in (
    'instagram',
    'facebook',
    'threads',
    'tiktok',
    'youtube',
    'twitter',
    'linkedin',
    'pinterest',
    'other'
  )),

  platform_post_id text,          -- platform or Blotato post id
  platform_post_url text,         -- live URL to the post
  title text,
  description text,
  thumbnail_url text,

  is_paid boolean not null default false,    -- ad vs organic
  experiment_id uuid,                        -- references content_experiments (defined later)
  variant_label text,                        -- e.g. "Title A / Thumb 1"

  scheduled_at timestamptz,
  published_at timestamptz,

  created_at timestamptz not null default now()
);

create index if not exists idx_content_variants_content_platform
  on content_variants (content_id, platform);

create index if not exists idx_content_variants_platform_post
  on content_variants (platform, platform_post_id);
