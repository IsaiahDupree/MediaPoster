-- Migration: Seed Platform Text Constraints with Official Limits
-- Sources: Official platform documentation (linked in source_url)
-- Target: 80% under max (target_margin_pct = 0.20)

-- =====================================================
-- YouTube (titles 100, descriptions 5000)
-- Source: https://support.google.com/youtube/answer/57404
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('youtube','video','title',100,80,'graphemes','https://support.google.com/youtube/answer/57404','official'),
('youtube','video','description',5000,4000,'graphemes','https://support.google.com/youtube/answer/57404','official'),
('youtube','short','title',100,80,'graphemes','https://support.google.com/youtube/answer/57404','official'),
('youtube','short','description',5000,4000,'graphemes','https://support.google.com/youtube/answer/57404','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Instagram (caption 2200; 30 hashtags, 20 @ tags)
-- Source: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, max_hashtags, max_mentions, count_rule, source_url, source_quality)
VALUES
('instagram','feed','caption',2200,1760,30,20,'graphemes','https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/','official'),
('instagram','reel','caption',2200,1760,30,20,'graphemes','https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/','official'),
('instagram','story','caption',2200,1760,30,20,'graphemes','https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  max_hashtags = EXCLUDED.max_hashtags,
  max_mentions = EXCLUDED.max_mentions,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- TikTok (caption max 2200 UTF-16 code units)
-- Source: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('tiktok','video','caption',2200,1760,'utf16','https://developers.tiktok.com/doc/content-posting-api-reference-direct-post','official'),
('tiktok','video','title',150,120,'utf16','https://developers.tiktok.com/doc/content-posting-api-reference-direct-post','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- LinkedIn (post 3000 chars)
-- Source: https://www.linkedin.com/help/linkedin/answer/a528176
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('linkedin','post','caption',3000,2400,'graphemes','https://www.linkedin.com/help/linkedin/answer/a528176','official'),
('linkedin','article','title',100,80,'graphemes','https://www.linkedin.com/help/linkedin/answer/a528176','official'),
('linkedin','article','description',120000,5000,'graphemes','https://www.linkedin.com/help/linkedin/answer/a528176','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- X/Twitter (standard 280; long posts up to 25,000)
-- Source: https://docs.x.com/fundamentals/counting-characters
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('x','standard_post','caption',280,224,'graphemes','https://docs.x.com/fundamentals/counting-characters','official'),
('x','long_post','caption',25000,2000,'graphemes','https://help.x.com/en/using-x/types-of-posts','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Threads (posts 500 UTF-8 bytes; attachments up to 10,000)
-- Source: https://developers.facebook.com/docs/threads/posts/
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('threads','post','caption',500,400,'utf8_bytes','https://developers.facebook.com/docs/threads/posts/','official'),
('threads','text_attachment','description',10000,8000,'utf8_bytes','https://about.fb.com/news/2025/09/attach-text-threads-posts-share-longer-perspectives/','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Pinterest (Title 100, Description 800)
-- Source: https://help.pinterest.com/en/business/article/pinterest-product-specs
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('pinterest','pin','title',100,80,'graphemes','https://help.pinterest.com/en/business/article/pinterest-product-specs','official'),
('pinterest','pin','description',800,640,'graphemes','https://help.pinterest.com/en/business/article/pinterest-product-specs','official')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Facebook (widely cited 63,206; use soft cap for performance)
-- Source: https://blog.hubspot.com/marketing/character-count-guide (public reference)
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality, notes)
VALUES
('facebook','post','caption',63206,1000,'graphemes','https://blog.hubspot.com/marketing/character-count-guide','public','Hard limit not clearly documented; use soft cap for performance.'),
('facebook','reel','caption',2200,1760,'graphemes','https://blog.hubspot.com/marketing/character-count-guide','public','Reels follow similar limits to Instagram.')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- =====================================================
-- Snapchat Spotlight
-- Source: Public documentation
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('snapchat','spotlight','caption',160,128,'graphemes','https://support.snapchat.com/en-US/article/spotlight','public')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Reddit
-- Source: Reddit API documentation
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('reddit','post','title',300,240,'graphemes','https://www.reddit.com/wiki/markdown','public'),
('reddit','post','caption',40000,5000,'graphemes','https://www.reddit.com/wiki/markdown','public')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();

-- =====================================================
-- Bluesky
-- Source: https://bsky.social/about/blog
-- =====================================================
INSERT INTO platform_text_constraints(platform, surface, field, max_chars, soft_cap_chars, count_rule, source_url, source_quality)
VALUES
('bluesky','post','caption',300,240,'graphemes','https://bsky.social/about/blog','public')
ON CONFLICT (platform, surface, field) DO UPDATE SET
  max_chars = EXCLUDED.max_chars,
  soft_cap_chars = EXCLUDED.soft_cap_chars,
  source_url = EXCLUDED.source_url,
  updated_at = NOW();
