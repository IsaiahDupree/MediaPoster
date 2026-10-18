# PRD: Modal Voice Cloning Integration

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** Medium  
**Estimated Effort:** 1-2 weeks  
**External Repo:** https://github.com/IsaiahDupree/ai-video-platform

---

## Executive Summary

Integrate Modal-hosted AI voice cloning capabilities into MediaPoster to enable personalized audio content generation. This allows creators to generate voiceovers in their own voice (or custom voices) for video content, narrations, and audio posts without recording new audio each time.

---

## Problem Statement

### Current State
- Video content requires manual voice recording
- No text-to-speech with custom voices
- Creators must re-record for each piece of content
- No integration with existing video pipeline

### User Pain Points
1. Time-consuming voice recording for each video
2. Inconsistent audio quality across recordings
3. Cannot scale voice content production
4. No way to maintain brand voice across content

---

## Goals & Success Metrics

### Goals
1. Enable one-click voiceover generation from text
2. Clone creator's voice from short reference samples
3. Integrate with Content Repurposing Engine
4. Support multiple voice profiles per account

### Success Metrics

| Metric | Target |
|--------|--------|
| Voice clone quality (MOS score) | > 4.0/5.0 |
| Generation latency | < 10 seconds per 30s audio |
| User adoption | 40% of video creators |
| Cost per minute of audio | < $0.05 |

---

## Features

### Phase 1: Voice Profile Management (Week 1)

#### 1.1 Voice Reference Upload
- **Supported formats:** WAV, MP3, M4A, FLAC
- **Recommended duration:** 10-30 seconds
- **Quality requirements:** Clear speech, minimal background noise
- **Multiple samples:** Up to 5 reference clips per voice

#### 1.2 Voice Profile Storage
- Store voice embeddings in database
- Link to user account
- Support multiple voices per user (personal, character, brand)
- Voice profile naming and organization

#### 1.3 Voice Quality Analysis
- Automatic quality scoring of reference audio
- Feedback on improving reference quality
- Background noise detection
- Speech clarity assessment

### Phase 2: Voice Generation API (Week 1-2)

#### 2.1 Text-to-Speech Generation
- **Input:** Text + voice profile ID
- **Output:** Generated audio file (WAV/MP3)
- **Max length:** 5 minutes per request
- **Languages:** English (primary), 10+ additional

#### 2.2 Generation Options
| Option | Description |
|--------|-------------|
| Speed | 0.5x - 2.0x playback rate |
| Pitch | -50% to +50% adjustment |
| Emotion | Neutral, happy, serious, excited |
| Stability | Voice consistency vs expressiveness |

#### 2.3 Batch Generation
- Generate multiple clips in parallel
- Queue management for large jobs
- Progress tracking and notifications

### Phase 3: Integration Points (Week 2)

#### 3.1 Content Repurposing Integration
- Auto-generate voiceovers for clips
- Replace original audio with cloned voice
- Multi-language dubbing support

#### 3.2 Video Editor Integration
- Voice preview in editor
- Sync to video timeline
- Multiple voice tracks

#### 3.3 Scheduling Integration
- Generate voice at schedule time
- Platform-specific audio optimization

---

## Technical Architecture

### External Service (Modal)

**Endpoint:** Modal-hosted serverless function  
**Documentation:** `ai-video-platform/docs/MODAL_VOICE_CLONING.md`

```
POST /clone-voice
Content-Type: multipart/form-data

Parameters:
- voice_reference: audio file (WAV/MP3)
- text: string (text to synthesize)
- options: JSON (speed, pitch, emotion)

Response:
- audio_url: string (generated audio URL)
- duration_seconds: float
- processing_time_ms: int
```

### Database Schema

```sql
-- Voice profiles
CREATE TABLE voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Reference audio
    reference_urls JSONB DEFAULT '[]',
    
    -- Voice embedding (from Modal)
    embedding_id VARCHAR(255),
    embedding_created_at TIMESTAMPTZ,
    
    -- Quality metrics
    quality_score FLOAT,
    quality_notes TEXT,
    
    -- Settings
    default_speed FLOAT DEFAULT 1.0,
    default_emotion VARCHAR(20) DEFAULT 'neutral',
    
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated audio
CREATE TABLE voice_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    voice_profile_id UUID REFERENCES voice_profiles(id),
    
    -- Input
    input_text TEXT NOT NULL,
    options JSONB DEFAULT '{}',
    
    -- Output
    output_url TEXT,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,
    
    -- Processing
    status VARCHAR(20) DEFAULT 'pending',
    modal_job_id VARCHAR(255),
    processing_time_ms INTEGER,
    
    -- Cost tracking
    cost_credits FLOAT,
    
    -- Usage
    used_in_clip_id UUID,
    used_in_post_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_voice_profiles_user ON voice_profiles(user_id);
CREATE INDEX idx_voice_generations_user ON voice_generations(user_id, created_at DESC);
CREATE INDEX idx_voice_generations_status ON voice_generations(status);
```

### API Endpoints

```
# Voice Profiles
POST   /api/voice/profiles                    # Create voice profile
GET    /api/voice/profiles                    # List user's profiles
GET    /api/voice/profiles/{id}               # Get profile details
PUT    /api/voice/profiles/{id}               # Update profile
DELETE /api/voice/profiles/{id}               # Delete profile
POST   /api/voice/profiles/{id}/reference     # Upload reference audio
POST   /api/voice/profiles/{id}/analyze       # Analyze voice quality

# Generation
POST   /api/voice/generate                    # Generate audio from text
GET    /api/voice/generate/{id}               # Get generation status
GET    /api/voice/generate/{id}/download      # Download generated audio
POST   /api/voice/generate/batch              # Batch generation

# Usage & Analytics
GET    /api/voice/usage                       # Usage stats and costs
GET    /api/voice/history                     # Generation history
```

### Service Implementation

```python
# Backend/services/voice/modal_voice_service.py

import httpx
from typing import Optional

class ModalVoiceService:
    """
    Client for Modal-hosted voice cloning API
    """
    
    def __init__(self, endpoint_url: str, api_key: str):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        
    async def clone_voice(
        self,
        text: str,
        voice_reference_url: str,
        options: Optional[dict] = None
    ) -> dict:
        """
        Generate cloned voice audio from text
        
        Args:
            text: Text to synthesize
            voice_reference_url: URL to reference audio
            options: Speed, pitch, emotion settings
            
        Returns:
            {audio_url, duration_seconds, processing_time_ms}
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint_url,
                json={
                    "text": text,
                    "voice_reference": voice_reference_url,
                    "options": options or {}
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
            
    async def analyze_reference(
        self,
        audio_url: str
    ) -> dict:
        """
        Analyze reference audio quality
        
        Returns:
            {quality_score, issues, recommendations}
        """
        # Quality analysis implementation
        pass
```

### File Structure

```
Backend/
├── services/
│   └── voice/
│       ├── __init__.py
│       ├── modal_voice_service.py    # Modal API client
│       ├── voice_profile_service.py  # Profile management
│       ├── generation_service.py     # Generation orchestration
│       └── quality_analyzer.py       # Reference quality analysis
├── api/
│   └── endpoints/
│       └── voice_api.py              # API routes

dashboard/
├── app/
│   └── (dashboard)/
│       └── voice/
│           ├── page.tsx              # Voice profiles list
│           ├── new/
│           │   └── page.tsx          # Create profile
│           └── generate/
│               └── page.tsx          # Generation interface
├── components/
│   └── voice/
│       ├── VoiceProfileCard.tsx
│       ├── ReferenceUploader.tsx
│       ├── GenerationForm.tsx
│       └── AudioPreview.tsx
```

---

## User Interface

### Voice Profile Manager
```
┌─────────────────────────────────────────────────────────┐
│  Voice Profiles                        [+ New Profile]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🎤 My Voice                          ⭐ Default  │   │
│  │    Quality: 4.2/5.0 • 3 references              │   │
│  │    [Generate] [Edit] [Preview]                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🎤 Professional Narrator                        │   │
│  │    Quality: 4.5/5.0 • 2 references              │   │
│  │    [Generate] [Edit] [Preview]                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Generation Interface
```
┌─────────────────────────────────────────────────────────┐
│  Generate Voice                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Voice Profile: [My Voice ▼]                           │
│                                                         │
│  Text to speak:                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Welcome to this week's video! Today we're       │   │
│  │ going to explore the top 5 productivity tips... │   │
│  └─────────────────────────────────────────────────┘   │
│  Characters: 89 • Est. duration: 12 seconds            │
│                                                         │
│  Options:                                               │
│  Speed: [1.0x ▼]  Emotion: [Neutral ▼]                 │
│                                                         │
│  [Preview] [Generate & Download]                        │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  Recent Generations                                     │
│  • "Welcome to this week..." (12s) - 2 min ago [▶️]    │
│  • "Thanks for watching..." (8s) - 1 hr ago [▶️]       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Integration Examples

### TypeScript Client
```typescript
// dashboard/lib/services/voice-service.ts

export class VoiceService {
  private baseUrl = process.env.NEXT_PUBLIC_API_URL;
  
  async generateVoice(
    profileId: string,
    text: string,
    options?: VoiceOptions
  ): Promise<VoiceGeneration> {
    const response = await fetch(`${this.baseUrl}/api/voice/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        voice_profile_id: profileId,
        text,
        options
      })
    });
    return response.json();
  }
  
  async getProfiles(): Promise<VoiceProfile[]> {
    const response = await fetch(`${this.baseUrl}/api/voice/profiles`);
    return response.json();
  }
}
```

### Python Integration
```python
# Backend usage example

from services.voice import ModalVoiceService

voice_service = ModalVoiceService(
    endpoint_url=os.getenv("MODAL_VOICE_ENDPOINT"),
    api_key=os.getenv("MODAL_API_KEY")
)

# Generate voiceover for a clip
result = await voice_service.clone_voice(
    text="Welcome to today's video!",
    voice_reference_url="https://storage.../my-voice.wav",
    options={"speed": 1.0, "emotion": "excited"}
)

audio_url = result["audio_url"]
```

---

## Voice Reference Best Practices

### Optimal Reference Audio

| Attribute | Recommendation |
|-----------|----------------|
| Duration | 10-30 seconds |
| Format | WAV (lossless) preferred |
| Sample rate | 44.1kHz or 48kHz |
| Background | Silent or minimal noise |
| Content | Natural speech, varied tones |
| Quality | Clear, no clipping or distortion |

### Common Issues

| Issue | Impact | Solution |
|-------|--------|----------|
| Too short (<5s) | Poor clone quality | Use longer reference |
| Background noise | Voice artifacts | Record in quiet space |
| Multiple speakers | Confused model | Single speaker only |
| Low quality | Distorted output | Re-record with better mic |

---

## Cost Estimation

### Modal Pricing (Serverless GPU)

| Resource | Cost | Notes |
|----------|------|-------|
| A10G GPU | $0.000463/sec | ~$1.67/hour |
| Storage | $0.20/GB/month | Reference audio |
| Bandwidth | $0.15/GB | Generated audio |

### Estimated Usage Costs

| Usage Level | Monthly Generations | Est. Cost |
|-------------|---------------------|-----------|
| Light | 100 clips (50 min) | ~$5 |
| Medium | 500 clips (250 min) | ~$20 |
| Heavy | 2000 clips (1000 min) | ~$75 |

---

## Implementation Timeline

| Day | Task |
|-----|------|
| 1-2 | Database schema, voice profile service |
| 3-4 | Modal API integration, generation service |
| 5 | API endpoints, quality analyzer |
| 6-7 | Frontend: profile management |
| 8-9 | Frontend: generation interface |
| 10 | Integration with repurposing engine |
| 11-12 | Testing, documentation |

---

## Dependencies

- **Modal:** Serverless GPU hosting
- **External repo:** `ai-video-platform` (voice model hosting)
- **Storage:** S3/Supabase for audio files
- **FFmpeg:** Audio format conversion

---

## Security Considerations

1. **Voice consent:** Users must confirm ownership/rights to reference voice
2. **Usage limits:** Prevent abuse with rate limiting
3. **Content filtering:** Block generation of harmful content
4. **Data retention:** Clear policy on voice data storage

---

## Future Enhancements

1. **Real-time cloning:** Stream audio as it generates
2. **Voice marketplace:** Share/sell voice profiles
3. **Multi-speaker:** Dialogue with multiple cloned voices
4. **Emotion detection:** Auto-detect emotion from text
5. **Background music:** Auto-mix with generated voice

---

**Document Owner:** Engineering Team  
**Last Updated:** January 19, 2026  
**External Docs:** https://github.com/IsaiahDupree/ai-video-platform/docs/MODAL_VOICE_CLONING.md
