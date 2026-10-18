# PRD: Cross-Platform DM Automation System

**Version:** 1.0  
**Date:** January 25, 2026  
**Status:** In Development  
**Priority:** High  
**Estimated Effort:** 3-4 weeks

---

## Executive Summary

This PRD defines the **Cross-Platform Direct Message (DM) Automation System** for MediaPoster. The system enables automated reading, sending, syncing, and AI-assisted responses for DMs across Twitter/X, TikTok, Instagram, and Threads platforms.

---

## Current Implementation Status

### Existing Files

| Platform | File | Location | Status |
|----------|------|----------|--------|
| **Twitter/X** | `safari_twitter_dm.py` | `Backend/automation/` | ✅ Implemented |
| **TikTok** | `tiktok_messenger.py` | `Backend/automation/` | ✅ Implemented |
| **Instagram** | `safari_instagram_poster.py` | `Backend/automation/` | ✅ Implemented |
| **Threads** | N/A | - | ❌ No DMs (platform limitation) |

### Capability Matrix

| Capability | Twitter | TikTok | Instagram |
|------------|---------|--------|-----------|
| Login verification | ✅ | ✅ | ✅ |
| Navigate to inbox | ✅ | ✅ | ✅ |
| List conversations | ⚠️ Partial | ✅ | ✅ |
| Read messages | ❌ | ✅ | ✅ |
| Send messages | ✅ | ✅ | ✅ |
| Search users | ✅ | ✅ | ❌ |
| Rate limiting | ✅ | ❌ | ❌ |
| Database sync | ❌ | ❌ | ❌ |
| AI responses | ❌ | ❌ | ❌ |

---

## Goals

1. **Unified DM Management**: Single API/dashboard for all platforms
2. **Database Sync**: Store all DM conversations in Supabase
3. **AI-Assisted Replies**: Generate contextual responses using AI
4. **Rate Limiting**: Respect platform limits to avoid suspension
5. **Real-time Polling**: Background job to check for new messages
6. **Permission Gate**: Only send links after consent (safety guardrail)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard (Community Inbox UI)                                 │
│  - Unified inbox view                                           │
│  - Quick reply templates                                        │
│  - AI suggestion button                                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  DM Service (Backend/services/dm/)                              │
│  - DMService: High-level API                                    │
│  - DMSyncWorker: Background polling                             │
│  - DMTracker: Database persistence                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Event Bus
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Platform Adapters                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Twitter DM  │ │ TikTok DM   │ │ Instagram   │               │
│  │ Adapter     │ │ Adapter     │ │ DM Adapter  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Safari AppleScript
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Safari Browser (macOS)                                         │
│  - Logged into all platforms                                    │
│  - Session management via SafariSessionManager                  │
└─────────────────────────────────────────────────────────────────┘
```

### Event Topics

| Topic | Description | Payload |
|-------|-------------|---------|
| `dm.sync.requested` | Request to sync DMs from platform | `{platform, account_id}` |
| `dm.sync.completed` | Sync finished | `{platform, new_count, total}` |
| `dm.received` | New DM received | `{platform, sender, content, conversation_id}` |
| `dm.sent` | DM sent successfully | `{platform, recipient, content, dm_id}` |
| `dm.reply.suggested` | AI generated reply | `{conversation_id, suggestion, confidence}` |
| `dm.failed` | DM operation failed | `{platform, error, operation}` |

---

## Database Schema

```sql
-- DM Conversations
CREATE TABLE dm_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL,          -- twitter, tiktok, instagram
    account_id VARCHAR(50) NOT NULL,        -- Our account ID
    participant_username VARCHAR(100) NOT NULL,
    participant_display_name VARCHAR(200),
    is_group BOOLEAN DEFAULT false,
    last_message_at TIMESTAMPTZ,
    unread_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',    -- active, archived, blocked
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, account_id, participant_username)
);

-- DM Messages
CREATE TABLE dm_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES dm_conversations(id),
    platform_message_id VARCHAR(100),       -- Platform's message ID
    sender_username VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text', -- text, image, video, link
    is_from_us BOOLEAN DEFAULT false,
    is_read BOOLEAN DEFAULT false,
    ai_generated BOOLEAN DEFAULT false,
    template_id UUID,                        -- If from template
    sentiment VARCHAR(20),                   -- positive, neutral, negative
    intent VARCHAR(50),                      -- question, feedback, complaint, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(conversation_id, platform_message_id)
);

-- DM Templates (Quick Replies)
CREATE TABLE dm_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),                    -- greeting, followup, cta, etc.
    use_count INTEGER DEFAULT 0,
    avg_response_rate FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- DM Rate Limits
CREATE TABLE dm_rate_limits (
    platform VARCHAR(20) PRIMARY KEY,
    daily_limit INTEGER NOT NULL DEFAULT 50,
    hourly_limit INTEGER NOT NULL DEFAULT 10,
    min_delay_seconds INTEGER DEFAULT 30,
    max_delay_seconds INTEGER DEFAULT 120,
    is_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default limits
INSERT INTO dm_rate_limits (platform, daily_limit, hourly_limit) VALUES
    ('twitter', 50, 10),
    ('tiktok', 100, 20),
    ('instagram', 75, 15);

-- Indexes
CREATE INDEX idx_dm_conversations_platform ON dm_conversations(platform);
CREATE INDEX idx_dm_messages_conversation ON dm_messages(conversation_id);
CREATE INDEX idx_dm_messages_created ON dm_messages(created_at);
```

---

## API Endpoints

### GET `/api/dm/inbox`

Get unified inbox across all platforms.

**Response:**
```json
{
    "conversations": [
        {
            "id": "uuid",
            "platform": "twitter",
            "participant": "@video_creator",
            "last_message": "Love your content!",
            "timestamp": "2026-01-25T14:30:00Z",
            "unread": true
        }
    ],
    "total_unread": 12,
    "platforms": {
        "twitter": {"unread": 3, "total": 45},
        "tiktok": {"unread": 5, "total": 67},
        "instagram": {"unread": 4, "total": 89}
    }
}
```

### GET `/api/dm/conversation/{id}`

Get messages from a specific conversation.

### POST `/api/dm/send`

Send a DM.

```json
{
    "platform": "twitter",
    "recipient": "username",
    "message": "Hey! Thanks for reaching out.",
    "template_id": "optional-uuid"
}
```

### POST `/api/dm/sync`

Trigger sync for platform(s).

```json
{
    "platform": "all"  // or "twitter", "tiktok", "instagram"
}
```

### POST `/api/dm/suggest-reply`

Get AI-generated reply suggestion.

```json
{
    "conversation_id": "uuid",
    "context_messages": 5
}
```

---

## Components to Build

### 1. DMService (`services/dm/dm_service.py`)

```python
class DMService:
    """High-level API for DM management."""
    
    async def get_inbox(self, platforms: List[str] = None) -> InboxResponse:
        """Get unified inbox."""
        
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get conversation with messages."""
        
    async def send_dm(self, platform: str, recipient: str, 
                      message: str) -> SendResult:
        """Send a DM with rate limiting."""
        
    async def sync_platform(self, platform: str) -> SyncResult:
        """Sync DMs from platform to database."""
        
    async def suggest_reply(self, conversation_id: str) -> str:
        """Get AI-generated reply suggestion."""
```

### 2. DMSyncWorker (`services/workers/dm_sync_worker.py`)

```python
class DMSyncWorker(BaseWorker):
    """Background worker for DM synchronization."""
    
    SYNC_INTERVAL = 1800  # 30 minutes
    
    async def handle_event(self, event: Event):
        """Handle dm.sync.requested events."""
        
    async def run_periodic_sync(self):
        """Sync all platforms periodically."""
```

### 3. Platform Adapters

Extend existing automation files:

```python
# services/dm/adapters/twitter_dm_adapter.py
class TwitterDMAdapter:
    def __init__(self, safari_dm: SafariTwitterDM):
        self.safari = safari_dm
    
    async def get_conversations(self) -> List[Conversation]:
        """Fetch conversations from Twitter."""
    
    async def get_messages(self, conversation_id: str) -> List[Message]:
        """Fetch messages from conversation."""
    
    async def send_message(self, recipient: str, text: str) -> bool:
        """Send DM to recipient."""
```

---

## Safety Guardrails

### DM Permission Gate

```python
PERMISSION_GATE_RULES = {
    # Links only allowed after:
    "link_allowed_after": [
        "user_consented",       # User said "yes" or "send it"
        "asset_delivered",      # We delivered a promised resource
        "explicit_request"      # User asked for link
    ],
    
    # Blocked actions
    "never_allowed": [
        "unsolicited_links",
        "spam_patterns",
        "aggressive_ctas"
    ],
    
    # Rate limits
    "per_user_per_day": 3,      # Max DMs to same user/day
    "offer_fatigue_hours": 72   # Hours between direct CTAs
}
```

### Blocklist Patterns

```python
BLOCKLIST_PATTERNS = [
    r"click here now",
    r"limited time only",
    r"act fast",
    r"buy now",
    r"100% guaranteed"
]
```

---

## Test Plan

### Unit Tests

1. **DMService Tests**
   - `test_get_inbox_returns_all_platforms`
   - `test_send_dm_respects_rate_limit`
   - `test_sync_stores_messages_in_db`

2. **Adapter Tests**
   - `test_twitter_adapter_parses_conversations`
   - `test_tiktok_adapter_sends_message`
   - `test_instagram_adapter_reads_messages`

3. **Safety Tests**
   - `test_permission_gate_blocks_unsolicited_links`
   - `test_rate_limit_enforced_per_user`
   - `test_blocklist_patterns_detected`

### Integration Tests

1. **End-to-End Flow**
   - `test_full_dm_sync_flow`
   - `test_send_and_verify_dm`
   - `test_ai_reply_generation`

2. **Cross-Platform**
   - `test_unified_inbox_all_platforms`
   - `test_platform_specific_rate_limits`

### Performance Tests

1. **Sync Performance**
   - Sync 100 conversations in < 5 minutes
   - Memory usage < 500MB during sync

2. **Response Latency**
   - API response < 200ms
   - AI suggestion < 3 seconds

---

## Rollout Plan

### Phase 1: Database & Sync (Week 1-2)
- [ ] Create database schema
- [ ] Build DMService
- [ ] Build DMSyncWorker
- [ ] Manual sync working

### Phase 2: API & Dashboard (Week 2-3)
- [ ] REST API endpoints
- [ ] Community Inbox UI
- [ ] Quick reply templates

### Phase 3: AI & Automation (Week 3-4)
- [ ] AI reply suggestions
- [ ] Permission gate enforcement
- [ ] Automated polling
- [ ] Safety guardrails

### Phase 4: Polish & Scale (Week 4+)
- [ ] Performance optimization
- [ ] Error handling
- [ ] Analytics dashboard
- [ ] Multi-account support

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Sync latency | < 30 seconds per platform |
| Message delivery rate | > 99% |
| AI suggestion acceptance | > 40% |
| Response time reduction | > 50% vs manual |
| Zero unsolicited links | 100% compliance |

---

## Dependencies

| Dependency | Status |
|------------|--------|
| Safari automation files | ✅ Complete |
| SafariSessionManager | ✅ Complete |
| Event bus | ✅ Complete |
| Supabase connection | ✅ Complete |
| AI comment generator | ✅ Can be adapted |
| Frontend dashboard | ⚠️ Needs Community Inbox page |

---

**Document Owner:** Development Team  
**Last Updated:** January 25, 2026  
**Next Review:** February 1, 2026
