# EverReach 30-Day Content Calendar System

## Product Requirements Document (PRD)

**Version**: 1.0.0  
**Created**: December 30, 2024  
**Status**: Ready for Implementation

---

## 1. Overview

### 1.1 Product Vision
EverReach is a relationship-focused content marketing system that drives waitlist signups through organic social content. The system generates, schedules, and posts content across multiple platforms following a strategic 30-day calendar.

### 1.2 Primary Goal
Drive waitlist signups to **everreach.app/waitlist** through organic social content.

### 1.3 Brand Voice
- **Tone**: Direct, slightly provocative, empathetic to the pain
- **Voice**: Founder/expert who's been there
- **No-go**: Overly salesy, corporate, or generic

---

## 2. Content Pillars

| Pillar | % of Content | Purpose | Example Themes |
|--------|--------------|---------|----------------|
| Pain Point Agitation | 40% | Make the problem feel urgent | Network dying, forgotten contacts |
| Educational Value | 30% | Position as the expert | Frameworks, tips, systems |
| Social Proof / Results | 20% | Build trust | Testimonials, case studies |
| Behind-the-Scenes | 10% | Build connection | Founder story, product sneak peeks |

---

## 3. Platform Strategy

### 3.1 LinkedIn
- **Best for**: Professional networking pain, B2B relationships
- **Formats**: Text posts (1300 chars), carousels (8-10 slides), polls
- **Timing**: Tue-Thu, 8-10am or 5-6pm EST
- **Hashtags**: #networking #relationships #sales #founders (max 3-5)
- **Engagement**: Reply to comments within 1 hour

### 3.2 Twitter/X
- **Best for**: Hot takes, threads, quick tips
- **Formats**: Single tweets, threads (5-10 tweets), quote tweets
- **Timing**: 8am, 12pm, 5pm, 9pm EST
- **Engagement**: Reply to networking/sales influencers

### 3.3 Instagram
- **Best for**: Visual storytelling, younger audience
- **Formats**: Reels (15-30s), carousels, Stories
- **Timing**: 11am-1pm, 7-9pm EST
- **Hooks**: First frame is everything
- **Audio**: Use trending sounds when appropriate

### 3.4 TikTok
- **Best for**: Raw, authentic, problem-focused content
- **Formats**: Talking head, POV videos, stitches
- **Timing**: 7-9am, 12-3pm, 7-9pm EST
- **Hooks**: First 1 second is everything

---

## 4. CTA Strategy

| CTA Type | Frequency | When to Use | Example |
|----------|-----------|-------------|---------|
| No CTA (engagement) | 50% | Pain points, polls | "Anyone else feel this?" |
| Soft CTA | 30% | Educational content | "Follow for more" |
| Direct CTA | 20% | Conversion posts | "Link in bio" |

---

## 5. Content Calendar Structure

### Week 1: The Problem
- **Focus**: Establish pain, build empathy
- **Tone**: "I get it, this sucks"
- **CTA Ratio**: 80% no CTA, 20% soft

### Week 2: The Solution
- **Focus**: Introduce frameworks, hint at product
- **Tone**: "Here's what actually works"
- **CTA Ratio**: 60% no CTA, 30% soft, 10% direct

### Week 3: Building Trust
- **Focus**: Social proof, results, testimonials
- **Tone**: "See, it works"
- **CTA Ratio**: 50% no CTA, 30% soft, 20% direct

### Week 4: Conversion Push
- **Focus**: Urgency, waitlist push
- **Tone**: "Don't miss out"
- **CTA Ratio**: 30% no CTA, 30% soft, 40% direct

---

## 6. Database Schema

### 6.1 Content Calendar Table
```sql
CREATE TABLE everreach_content_calendar (
    id SERIAL PRIMARY KEY,
    day_number INTEGER NOT NULL,          -- 1-30
    week_number INTEGER NOT NULL,         -- 1-4
    content_pillar VARCHAR(50) NOT NULL,  -- pain_point, educational, social_proof, bts
    
    -- Content
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    cta_type VARCHAR(20),                 -- none, soft, direct
    cta_text TEXT,
    
    -- Platform variants
    linkedin_version TEXT,
    twitter_version TEXT,
    instagram_version TEXT,
    tiktok_version TEXT,
    
    -- Metadata
    content_type VARCHAR(50),             -- text, carousel, thread, reel, poll
    slide_count INTEGER,                  -- For carousels
    hashtags JSONB,
    
    -- Scheduling
    scheduled_date DATE,
    scheduled_time TIME,
    platforms JSONB,                      -- ["linkedin", "twitter", "instagram"]
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',   -- draft, scheduled, posted, failed
    posted_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_calendar_day ON everreach_content_calendar(day_number);
CREATE INDEX idx_calendar_status ON everreach_content_calendar(status);
```

### 6.2 Content Posts Table
```sql
CREATE TABLE everreach_posts (
    id SERIAL PRIMARY KEY,
    calendar_id INTEGER REFERENCES everreach_content_calendar(id),
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(255),
    
    -- Post details
    content TEXT NOT NULL,
    media_urls JSONB,
    
    -- Metrics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    posted_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_posts_platform ON everreach_posts(platform);
CREATE INDEX idx_posts_status ON everreach_posts(status);
```

---

## 7. API Endpoints

### 7.1 Calendar Management
```
GET  /api/v1/everreach/calendar
     List all calendar entries

GET  /api/v1/everreach/calendar/{day}
     Get specific day's content

POST /api/v1/everreach/calendar/generate
     AI-generate calendar content for all 30 days

PUT  /api/v1/everreach/calendar/{id}
     Update calendar entry

POST /api/v1/everreach/calendar/{id}/schedule
     Schedule entry for posting
```

### 7.2 Content Generation
```
POST /api/v1/everreach/generate/day
     Generate content for a specific day
     Body: { day_number, pillar, hook, platforms }

POST /api/v1/everreach/generate/week
     Generate content for entire week
     Body: { week_number }

POST /api/v1/everreach/generate/variants
     Generate platform variants for content
     Body: { content, platforms }
```

### 7.3 Posting
```
POST /api/v1/everreach/post
     Post content to platforms
     Body: { calendar_id, platforms }

POST /api/v1/everreach/post/batch
     Post multiple entries
     Body: { calendar_ids }

GET  /api/v1/everreach/posts/{calendar_id}
     Get post status and metrics
```

### 7.4 Analytics
```
GET  /api/v1/everreach/analytics/overview
     Get overall campaign metrics

GET  /api/v1/everreach/analytics/by-pillar
     Get metrics grouped by content pillar

GET  /api/v1/everreach/analytics/by-platform
     Get metrics grouped by platform

GET  /api/v1/everreach/analytics/top-performers
     Get top performing posts
```

---

## 8. AI Prompts

### 8.1 Pain Point Content
```
You are a founder who has personally experienced the pain of losing touch with valuable relationships. Write content that:

1. Opens with a hook that creates immediate recognition ("This is me")
2. Describes the specific pain in vivid detail
3. Uses short sentences for impact
4. Ends without a sales pitch (pure empathy)

Tone: Direct, slightly provocative, empathetic
Avoid: Salesy language, corporate speak, generic advice
```

### 8.2 Educational Content
```
You are an expert on relationship management and networking systems. Write content that:

1. Provides a specific, actionable framework
2. Uses numbers and concrete steps
3. Gives examples that readers can use immediately
4. Positions the reader as capable of solving this

Tone: Knowledgeable but accessible
Avoid: Condescension, complexity, theory without action
```

### 8.3 Social Proof Content
```
Write a testimonial-style story that:

1. Shows a real transformation (before → after)
2. Includes specific details that feel authentic
3. Highlights the "aha moment" when things clicked
4. Subtly points to the solution without hard selling

Tone: Genuine, specific, relatable
Avoid: Fake-sounding praise, vague claims, obvious sales pitch
```

---

## 9. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create database tables
- [ ] Build calendar CRUD API
- [ ] Implement content generation endpoints
- [ ] Create dashboard UI for calendar view

### Phase 2: AI Generation (Week 2)
- [ ] Build OpenAI prompts for each pillar
- [ ] Implement platform variant generation
- [ ] Add hashtag generation
- [ ] Create carousel slide generator

### Phase 3: Scheduling & Posting (Week 3)
- [ ] Integrate with Blotato for posting
- [ ] Build scheduling queue
- [ ] Add duplicate detection before posting
- [ ] Implement post status tracking

### Phase 4: Analytics & Optimization (Week 4)
- [ ] Build metrics collection
- [ ] Create analytics dashboard
- [ ] Add A/B testing for hooks
- [ ] Implement performance-based recommendations

---

## 10. Content Templates

### 10.1 Day 1 Template (Pain Point)
```
Hook: "Your network is dying while you scroll"

Body:
Your network is dying while you scroll.

That mentor who changed your career? Haven't talked in 8 months.
That client who referred you 3 people? Radio silence.
That friend from that conference? Forgot their name.

You don't have a networking problem.
You have a follow-up problem.

And it's costing you more than you realize.

CTA: None (engagement post)
Platforms: All
```

### 10.2 Day 2 Template (Educational - Carousel)
```
Hook: "The Warmth Score: How I rate every relationship"

Slides:
1. Title: The Warmth Score: How I Rate Every Relationship
2. Four categories: HOT/WARM/COOLING/COLD
3. The problem: 80% of networks are COLD
4. How to calculate your score
5. Industry benchmarks
6. The good news: You only need 50 warm relationships
7. CTA: Want help tracking automatically? [link]

Platforms: LinkedIn, Twitter (as thread), Instagram
```

### 10.3 Day 3 Template (Story)
```
Hook: "I lost a $50K deal because I forgot to follow up"

Body:
I lost a $50K deal because I forgot to follow up.

Met someone at a conference. Great conversation.
They said "let's connect next week."
I said "definitely."

Then life happened.

3 months later, I saw their LinkedIn post:
"Excited to announce we're working with [competitor]!"

That was MY deal. I just... forgot.

CTA: Soft - "Anyone else been there?"
Platforms: All
```

---

## 11. Metrics & Success Criteria

### 11.1 Primary Metrics
- **Waitlist signups per week**: Target 100+
- **Link clicks**: Track via UTM parameters
- **Engagement rate**: >5% on all posts

### 11.2 Secondary Metrics
- **Follower growth**: Track across platforms
- **Comment sentiment**: Positive mentions
- **DM inquiries**: People asking about the product

### 11.3 Content Metrics
- **Best performing pillars**: Which drives most signups
- **Best performing platforms**: Where to double down
- **Best posting times**: Refine schedule

---

## 12. Risk Mitigation

### 12.1 Duplicate Content
- Use Content Guard duplicate detection before posting
- Check similarity across all accounts
- Block posts >85% similar to previous content

### 12.2 Platform Bans
- Vary posting times slightly
- Don't post identical content cross-platform
- Add human review for flagged content

### 12.3 Low Engagement
- A/B test hooks weekly
- Adjust pillar ratios based on performance
- Increase behind-the-scenes if trust is low

---

## 13. Integration Points

### 13.1 MediaPoster
- Use ReelTrends for content generation
- Use Content Guard for duplicate detection
- Use Blotato integration for posting

### 13.2 External Services
- OpenAI for content generation
- Blotato for multi-platform posting
- RapidAPI for competitor research

---

*Last Updated: December 30, 2024*
