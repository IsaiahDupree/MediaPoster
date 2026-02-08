# PRD: AI Caption Variants

**Status:** Proposed
**Priority:** P1 — Medium-Term
**Effort:** ~2-3 days
**Impact:** Higher engagement per platform by matching native tone; eliminates copy-paste captions

---

## 1. Problem Statement

Currently, the same caption is posted to every platform. But each platform has a distinct culture and optimal caption format:
- **TikTok:** Casual, hook-driven, emoji-heavy, 3-5 hashtags
- **Instagram:** Storytelling, 20-30 hashtags in a separate block, CTA
- **YouTube:** SEO-focused description, timestamps, links
- **Twitter/X:** Punchy, <280 chars, 1-2 hashtags max
- **LinkedIn:** Professional, thought-leadership framing
- **Threads:** Conversational, opinion-based

Posting the same text everywhere leaves engagement on the table.

## 2. Objective

Use GPT to automatically rewrite each caption in the native tone and format of the target platform, while preserving the core message. Runs in the publish pipeline — zero manual effort.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Engagement rate improvement | ≥ 10% vs uniform captions |
| Caption quality (human review) | ≥ 90% approval rate |
| Processing time | < 3 seconds per caption variant |
| Coverage | All 9 supported platforms |

## 4. Technical Design

### 4.1 Architecture

```
Original Caption
       │
       ▼
┌──────────────────────┐
│  CaptionVariantEngine │  ← GPT-4o-mini per platform
│  (platform tone rules) │
└──────────┬───────────┘
           │  Platform-specific captions
           ▼
┌──────────────────────┐
│  Length Enforcer       │  ← Existing PLATFORM_LIMITS
│  (title + desc)       │
└──────────┬───────────┘
           │
           ▼
   BackgroundPublisher
```

### 4.2 Core Component (`services/caption_variant_engine.py`)

```python
class CaptionVariantEngine:
    PLATFORM_PROMPTS = {
        "tiktok": """Rewrite this caption for TikTok. Rules:
            - Start with a hook that stops the scroll (question, bold claim, or mystery)
            - Keep it casual and conversational
            - Use 2-3 relevant emojis
            - Add 3-5 trending hashtags at the end
            - Max 2200 characters
            Original: {caption}""",
        
        "instagram": """Rewrite this caption for Instagram Reels. Rules:
            - Start with a strong hook (first line is most important)
            - Tell a mini-story or share a lesson
            - End with a CTA (save this, share with someone, comment below)
            - Add a line break then 20-30 relevant hashtags
            - Max 2200 characters
            Original: {caption}""",
        
        "youtube": """Rewrite this as a YouTube video description. Rules:
            - First 2 lines are most important (shown before "Show more")
            - Include relevant keywords for SEO
            - Add a CTA to subscribe/like
            - Structure with line breaks for readability
            - Max 5000 characters
            Original: {caption}""",
        
        "twitter": """Rewrite this for Twitter/X. Rules:
            - Must be under 280 characters
            - Punchy and opinion-driven
            - Max 1-2 hashtags
            - No fluff — every word earns its place
            Original: {caption}""",
        
        "linkedin": """Rewrite this for LinkedIn. Rules:
            - Professional but authentic tone
            - Frame as a lesson or insight
            - Use line breaks for readability (1 sentence per line)
            - End with a question to drive comments
            - Max 3000 characters
            Original: {caption}""",
        
        "threads": """Rewrite this for Threads. Rules:
            - Conversational, opinion-based
            - Keep it under 500 characters
            - No hashtags
            - Feel like a text to a friend
            Original: {caption}""",
        
        "bluesky": """Rewrite this for Bluesky. Rules:
            - Under 300 characters
            - Casual, community-oriented
            - No hashtags
            Original: {caption}""",
        
        "pinterest": """Rewrite this as a Pinterest pin description. Rules:
            - SEO-focused with keywords
            - Describe what the viewer will learn/see
            - Max 500 characters
            Original: {caption}""",
        
        "facebook": """Rewrite this for Facebook. Rules:
            - Conversational and engaging
            - Ask a question or share a relatable moment
            - 2-3 relevant hashtags max
            Original: {caption}""",
    }
    
    async def generate_variant(self, caption: str, platform: str, title: str = None) -> str:
        """Generate a platform-specific caption variant using GPT"""
    
    async def generate_all_variants(self, caption: str, platforms: List[str]) -> Dict[str, str]:
        """Generate variants for multiple platforms in parallel"""
```

### 4.3 Integration Point

In `background_publisher.py`, replace the current `get_caption_for_platform` call:

```python
# After _build_caption returns the base caption:
if settings.get("use_caption_variants", True):
    variant_engine = CaptionVariantEngine()
    caption = await variant_engine.generate_variant(caption, platform_lower, title=request.title)
```

### 4.4 Caching

```sql
CREATE TABLE caption_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_caption_hash VARCHAR(64) NOT NULL,  -- SHA-256 of original
    platform VARCHAR(20) NOT NULL,
    variant_text TEXT NOT NULL,
    model_used VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(original_caption_hash, platform)
);
```

Same original caption → same variants (no re-generating for recycled posts unless explicitly refreshed).

### 4.5 Cost Estimate

- GPT-4o-mini: ~$0.15 / 1M input tokens, ~$0.60 / 1M output tokens
- Average caption: ~500 tokens in, ~300 tokens out
- Per variant: ~$0.0003
- Per post across 9 platforms: ~$0.003
- 100 posts/month across all platforms: ~$0.27/month

## 5. API Endpoints

```
POST /api/captions/generate-variant   — Generate variant for one platform
POST /api/captions/generate-all       — Generate variants for all platforms
GET  /api/captions/variants/:hash     — Get cached variants for a caption
```

## 6. Rollout Plan

1. **Phase 1:** Core engine + TikTok/Instagram/YouTube variants
2. **Phase 2:** All 9 platforms + caching
3. **Phase 3:** Dashboard preview (see all variants before publishing)
4. **Phase 4:** A/B test variants vs uniform captions

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GPT output exceeds platform limit | Run through existing PLATFORM_LIMITS truncation |
| Tone doesn't match creator voice | Include 2-3 example captions in prompt as few-shot examples |
| API latency delays publishing | Generate variants at schedule time, not publish time; cache results |
| Hallucinated hashtags | Post-process: validate hashtags exist or use known performing hashtags |

## 8. Out of Scope (v1)

- Creator voice fine-tuning (custom model)
- Multilingual caption variants
- Visual caption preview with platform mockup
- A/B testing between variant styles
