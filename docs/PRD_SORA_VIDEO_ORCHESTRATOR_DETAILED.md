# PRD: Sora Video Orchestrator (Detailed)

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T1.1 Video Intelligence  
**Effort:** 3-4 weeks  
**Priority:** 🔴 Critical

---

## Executive Summary

Build a multi-provider video generation orchestrator that transforms scripts into finished videos using AI video generators (Sora, Runway, Kling) with quality assessment, repair loops, and timeline assembly.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        SORA VIDEO ORCHESTRATOR                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         INPUT LAYER                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │   │
│  │  │   Script/Brief  │  │  Style Bible    │  │    Character Bible          │  │   │
│  │  │   (text/JSON)   │  │  (visual refs)  │  │    (@isaiahdupree)          │  │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘  │   │
│  │           └───────────────────┬┴─────────────────────────┘                   │   │
│  └───────────────────────────────┼──────────────────────────────────────────────┘   │
│                                  ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     DIRECTOR SERVICE                                         │   │
│  │                                                                              │   │
│  │   Script → Scene Breakdown → Shot List → Prompt Generation                  │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Input: "A story about overcoming challenges"                       │   │   │
│  │  │                                                                     │   │   │
│  │  │  Output: ClipPlan[                                                  │   │   │
│  │  │    {scene: 1, shot: "wide", prompt: "...", duration: 5s},          │   │   │
│  │  │    {scene: 1, shot: "close", prompt: "...", duration: 3s},         │   │   │
│  │  │    {scene: 2, shot: "medium", prompt: "...", duration: 4s},        │   │   │
│  │  │  ]                                                                  │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                  │                                                   │
│                                  ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     SCENE CRAFTER                                            │   │
│  │                                                                              │   │
│  │   Prompt Engineering + Style Baking + Character Consistency                 │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Base Prompt: "Person walking through city"                         │   │   │
│  │  │  + Style: "cinematic, 4K, dramatic lighting"                        │   │   │
│  │  │  + Character: "@isaiahdupree, African American male, beard"         │   │   │
│  │  │  + Context: "continuation from previous scene"                      │   │   │
│  │  │                                                                     │   │   │
│  │  │  = Final Prompt: "Cinematic 4K shot of @isaiahdupree, an African   │   │   │
│  │  │    American male with a beard, walking through a bustling city     │   │   │
│  │  │    at golden hour, dramatic lighting, continuation of journey..."  │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                  │                                                   │
│                                  ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     PROVIDER ROUTER                                          │   │
│  │                                                                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │   │
│  │  │      SORA       │  │     RUNWAY      │  │      KLING      │             │   │
│  │  │   (Primary)     │  │   (Fallback 1)  │  │   (Fallback 2)  │             │   │
│  │  │                 │  │                 │  │                 │             │   │
│  │  │  Safari Auto    │  │  API Direct     │  │  API Direct     │             │   │
│  │  │  @character     │  │  Gen-2/Gen-3    │  │  Kling AI       │             │   │
│  │  │  20s max        │  │  4s clips       │  │  5s clips       │             │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │   │
│  │           └───────────────────┬┴─────────────────────┘                      │   │
│  │                               ▼                                              │   │
│  │                    Provider Selection Logic:                                 │   │
│  │                    1. Check Sora credits available                           │   │
│  │                    2. If < 5 remaining, fallback to Runway                  │   │
│  │                    3. If Runway fails, try Kling                            │   │
│  │                    4. Queue for retry if all fail                           │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                  │                                                   │
│                                  ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                     ASSESSOR SERVICE                                         │   │
│  │                                                                              │   │
│  │   Quality Checks + Consistency Validation + Safety Review                   │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Assessment Criteria:                                               │   │   │
│  │  │                                                                     │   │   │
│  │  │  ✓ Prompt Adherence (Vision API)         Score: 0-100              │   │   │
│  │  │  ✓ Character Consistency                  Score: 0-100              │   │   │
│  │  │  ✓ Style Match                            Score: 0-100              │   │   │
│  │  │  ✓ Technical Quality (artifacts, blur)    Score: 0-100              │   │   │
│  │  │  ✓ Motion Smoothness                      Score: 0-100              │   │   │
│  │  │  ✓ Safety Check (no violations)           Pass/Fail                 │   │   │
│  │  │                                                                     │   │   │
│  │  │  Threshold: Overall score ≥ 70 = PASS                              │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                  │                                                   │
│                        ┌─────────┴─────────┐                                        │
│                        ▼                   ▼                                        │
│                   PASS (≥70)          FAIL (<70)                                    │
│                        │                   │                                        │
│                        ▼                   ▼                                        │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┐     │
│  │     TIMELINE ASSEMBLER      │  │           REPAIR LOOP                   │     │
│  │                             │  │                                         │     │
│  │  • Concatenate clips        │  │  Retry Strategies:                      │     │
│  │  • Add transitions          │  │  1. Refine prompt                       │     │
│  │  • Sync with audio          │  │  2. Change provider                     │     │
│  │  • Apply color grading      │  │  3. Adjust parameters                   │     │
│  │  • Export final video       │  │  4. Human review if 3x fail             │     │
│  │                             │  │                                         │     │
│  │  Tools: FFmpeg, MoviePy     │  │  Max retries: 3 per clip               │     │
│  └─────────────────────────────┘  └─────────────────────────────────────────┘     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_video_orchestrator.sql

-- Video Projects (overall container)
CREATE TABLE video_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    script TEXT,
    
    -- Bibles (for consistency)
    style_bible JSONB,
    -- {
    --   "visual_style": "cinematic, dramatic lighting",
    --   "color_palette": ["#1a1a2e", "#16213e", "#0f3460"],
    --   "aspect_ratio": "9:16",
    --   "reference_images": ["url1", "url2"]
    -- }
    
    character_bible JSONB,
    -- {
    --   "name": "@isaiahdupree",
    --   "description": "African American male, beard, athletic build",
    --   "reference_images": ["url1", "url2"],
    --   "voice_reference": "path/to/voice.wav"
    -- }
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, planning, generating, assembling, complete, failed
    progress INTEGER DEFAULT 0, -- 0-100
    
    -- Output
    output_path TEXT,
    output_url TEXT,
    duration_seconds FLOAT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Clip Plans (shot list)
CREATE TABLE clip_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES video_projects(id) ON DELETE CASCADE,
    
    -- Ordering
    scene_number INTEGER NOT NULL,
    shot_number INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL,
    
    -- Shot info
    shot_type VARCHAR(50), -- wide, medium, close, detail, pov
    shot_description TEXT,
    duration_seconds FLOAT NOT NULL,
    
    -- Prompts
    base_prompt TEXT NOT NULL,
    crafted_prompt TEXT, -- After scene crafter
    
    -- Provider preferences
    preferred_provider VARCHAR(20), -- sora, runway, kling
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, generating, assessing, approved, failed
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generation Attempts
CREATE TABLE generation_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_plan_id UUID REFERENCES clip_plans(id) ON DELETE CASCADE,
    
    -- Provider
    provider VARCHAR(20) NOT NULL, -- sora, runway, kling
    provider_job_id VARCHAR(255),
    
    -- Request
    prompt_used TEXT NOT NULL,
    parameters JSONB, -- {duration, aspect_ratio, style, etc}
    
    -- Result
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, complete, failed
    output_path TEXT,
    output_url TEXT,
    
    -- Assessment
    assessment_score FLOAT,
    assessment_details JSONB,
    -- {
    --   "prompt_adherence": 85,
    --   "character_consistency": 90,
    --   "style_match": 80,
    --   "technical_quality": 75,
    --   "motion_smoothness": 85,
    --   "safety_pass": true
    -- }
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_time_ms INTEGER
);

-- Final Timeline
CREATE TABLE video_timelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES video_projects(id) ON DELETE CASCADE,
    
    -- Timeline data
    clips JSONB NOT NULL,
    -- [
    --   {clip_id, start_time, end_time, transition_in, transition_out},
    --   ...
    -- ]
    
    -- Audio
    voiceover_path TEXT,
    music_path TEXT,
    sfx_paths JSONB,
    
    -- Output
    output_path TEXT,
    output_url TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rendered_at TIMESTAMPTZ
);

-- Provider Quotas (track usage)
CREATE TABLE provider_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(20) NOT NULL UNIQUE,
    
    -- Limits
    daily_limit INTEGER,
    monthly_limit INTEGER,
    
    -- Usage
    daily_used INTEGER DEFAULT 0,
    monthly_used INTEGER DEFAULT 0,
    
    -- Cost tracking
    cost_per_generation DECIMAL,
    total_spent DECIMAL DEFAULT 0,
    
    last_reset_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_clip_plans_project ON clip_plans(project_id);
CREATE INDEX idx_clip_plans_status ON clip_plans(status);
CREATE INDEX idx_attempts_clip ON generation_attempts(clip_plan_id);
CREATE INDEX idx_attempts_status ON generation_attempts(status);
```

---

## API Endpoints

### Projects

```yaml
# POST /api/video/projects
# Create new video project
Request:
  title: string
  script: string
  style_bible: object (optional)
  character_bible: object (optional)
Response:
  project: VideoProject

# GET /api/video/projects
# List all projects
Response:
  projects: VideoProject[]

# GET /api/video/projects/{id}
# Get project with clips
Response:
  project: VideoProject
  clip_plans: ClipPlan[]
  timeline: Timeline

# POST /api/video/projects/{id}/generate
# Start generation process
Response:
  job_id: string
  status: "started"

# GET /api/video/projects/{id}/status
# Get generation status
Response:
  status: string
  progress: number
  clips_complete: number
  clips_total: number
  current_step: string
```

### Director Service

```yaml
# POST /api/video/director/plan
# Generate clip plan from script
Request:
  script: string
  style: string (optional)
  max_clips: number (optional)
  target_duration: number (optional)
Response:
  clip_plans: ClipPlan[]
  estimated_duration: number

# POST /api/video/director/refine
# Refine existing plan
Request:
  project_id: uuid
  feedback: string
Response:
  clip_plans: ClipPlan[]
```

### Scene Crafter

```yaml
# POST /api/video/crafter/craft
# Craft prompts for clips
Request:
  clip_plan_id: uuid
  style_bible: object
  character_bible: object
Response:
  crafted_prompt: string
  provider_hints: object

# POST /api/video/crafter/batch
# Craft all prompts for project
Request:
  project_id: uuid
Response:
  clips_crafted: number
```

### Generation

```yaml
# POST /api/video/generate/clip
# Generate single clip
Request:
  clip_plan_id: uuid
  provider: string (optional)
Response:
  attempt_id: uuid
  status: "queued"

# POST /api/video/generate/batch
# Generate all clips for project
Request:
  project_id: uuid
  parallel: number (default: 3)
Response:
  job_id: string
  clips_queued: number

# GET /api/video/generate/status/{attempt_id}
# Get generation status
Response:
  status: string
  progress: number
  output_url: string (if complete)
```

### Assessment

```yaml
# POST /api/video/assess/{attempt_id}
# Assess generated clip
Response:
  score: number
  details: AssessmentDetails
  approved: boolean

# POST /api/video/assess/batch
# Assess all pending clips
Request:
  project_id: uuid
Response:
  assessed: number
  approved: number
  failed: number
```

### Timeline

```yaml
# POST /api/video/timeline/assemble
# Assemble final video
Request:
  project_id: uuid
  transitions: object (optional)
  audio: object (optional)
Response:
  job_id: string
  status: "assembling"

# GET /api/video/timeline/{project_id}
# Get timeline
Response:
  timeline: Timeline
  preview_url: string
```

---

## Core Services

### 1. Director Service
```python
# Backend/services/video_orchestrator/director_service.py

class DirectorService:
    """Transform scripts into shot lists."""
    
    async def create_clip_plan(
        self,
        script: str,
        style: str = "cinematic",
        target_duration: int = 60
    ) -> List[ClipPlan]:
        """Generate clip plan from script."""
        
        prompt = f"""
        You are a video director. Break down this script into a shot list.
        
        Script: {script}
        Style: {style}
        Target duration: {target_duration} seconds
        
        For each shot, provide:
        1. Scene number
        2. Shot type (wide, medium, close, detail, POV)
        3. Duration (3-10 seconds)
        4. Visual description for AI video generator
        5. Emotional tone
        
        Return JSON array of shots.
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return self.parse_clip_plans(response)
    
    async def estimate_duration(self, clips: List[ClipPlan]) -> float:
        """Calculate total duration."""
        return sum(clip.duration_seconds for clip in clips)
```

### 2. Scene Crafter
```python
# Backend/services/video_orchestrator/scene_crafter.py

class SceneCrafter:
    """Craft optimized prompts for video generation."""
    
    async def craft_prompt(
        self,
        clip: ClipPlan,
        style_bible: StyleBible,
        character_bible: CharacterBible,
        previous_clip: ClipPlan = None
    ) -> str:
        """Create provider-optimized prompt."""
        
        # Base prompt from clip plan
        base = clip.shot_description
        
        # Add style elements
        style_additions = self.format_style(style_bible)
        
        # Add character if present
        character_additions = ""
        if self.mentions_character(base, character_bible):
            character_additions = self.format_character(character_bible)
        
        # Add continuity from previous clip
        continuity = ""
        if previous_clip:
            continuity = f"Continuation from: {previous_clip.shot_description[:100]}"
        
        # Combine
        crafted = f"{base}. {character_additions}. {style_additions}. {continuity}"
        
        # Optimize for provider
        return self.optimize_for_provider(crafted, clip.preferred_provider)
    
    def optimize_for_provider(self, prompt: str, provider: str) -> str:
        """Apply provider-specific optimizations."""
        if provider == "sora":
            # Sora works well with @character mentions
            return prompt
        elif provider == "runway":
            # Runway prefers specific style keywords
            return f"{prompt}, cinematic, high quality, 4K"
        elif provider == "kling":
            # Kling prefers simpler prompts
            return self.simplify_prompt(prompt)
        return prompt
```

### 3. Provider Router
```python
# Backend/services/video_orchestrator/provider_router.py

class ProviderRouter:
    """Route generation requests to appropriate provider."""
    
    def __init__(self):
        self.providers = {
            "sora": SoraProvider(),
            "runway": RunwayProvider(),
            "kling": KlingProvider(),
        }
        self.preference_order = ["sora", "runway", "kling"]
    
    async def generate(
        self,
        clip: ClipPlan,
        preferred: str = None
    ) -> GenerationAttempt:
        """Generate clip using best available provider."""
        
        # Determine provider order
        providers_to_try = self.get_provider_order(preferred)
        
        for provider_name in providers_to_try:
            provider = self.providers[provider_name]
            
            # Check availability
            if not await provider.is_available():
                continue
            
            # Check quota
            if not await self.has_quota(provider_name):
                continue
            
            # Try generation
            try:
                result = await provider.generate(
                    prompt=clip.crafted_prompt,
                    duration=clip.duration_seconds
                )
                return result
            except ProviderError as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue
        
        raise AllProvidersFailedError("No providers available")
    
    async def has_quota(self, provider: str) -> bool:
        """Check if provider has remaining quota."""
        quota = await self.quota_repo.get(provider)
        return quota.daily_used < quota.daily_limit
```

### 4. Sora Provider (Safari Automation)
```python
# Backend/services/video_orchestrator/providers/sora_provider.py

class SoraProvider:
    """Generate videos using Sora via Safari automation."""
    
    def __init__(self):
        self.automation = SafariAutomation()
    
    async def generate(
        self,
        prompt: str,
        duration: int = 10
    ) -> GenerationResult:
        """Generate video using Sora."""
        
        # Check usage first
        usage = await self.automation.get_sora_usage()
        if usage.remaining < 1:
            raise QuotaExceededError("Sora quota exhausted")
        
        # Navigate to Sora
        await self.automation.navigate("https://sora.chatgpt.com/explore")
        
        # Enter prompt
        await self.automation.fill_textarea(prompt)
        
        # Start generation
        await self.automation.click_button("Create video")
        
        # Poll for completion
        result = await self.poll_for_completion(timeout=300)
        
        # Download result
        video_path = await self.download_video(result.video_url)
        
        return GenerationResult(
            provider="sora",
            video_path=video_path,
            video_url=result.video_url,
            prompt_used=prompt
        )
    
    async def poll_for_completion(self, timeout: int) -> dict:
        """Poll Sora activity page for completion."""
        start = time.time()
        while time.time() - start < timeout:
            status = await self.automation.check_generation_status()
            if status == "complete":
                return await self.automation.get_latest_video()
            elif status == "failed":
                raise GenerationFailedError("Sora generation failed")
            await asyncio.sleep(10)
        raise TimeoutError("Sora generation timed out")
```

### 5. Assessor Service
```python
# Backend/services/video_orchestrator/assessor_service.py

class AssessorService:
    """Assess quality of generated clips."""
    
    def __init__(self):
        self.vision = OpenAIVisionClient()
        self.threshold = 70
    
    async def assess(
        self,
        attempt: GenerationAttempt,
        clip: ClipPlan,
        style_bible: StyleBible,
        character_bible: CharacterBible
    ) -> Assessment:
        """Assess generated video quality."""
        
        # Extract frames for analysis
        frames = await self.extract_frames(attempt.output_path, count=5)
        
        # Run assessments
        scores = {
            "prompt_adherence": await self.assess_prompt_adherence(
                frames, clip.crafted_prompt
            ),
            "character_consistency": await self.assess_character(
                frames, character_bible
            ),
            "style_match": await self.assess_style(
                frames, style_bible
            ),
            "technical_quality": await self.assess_technical(
                frames
            ),
            "motion_smoothness": await self.assess_motion(
                attempt.output_path
            ),
        }
        
        # Safety check
        safety_pass = await self.safety_check(frames)
        
        # Calculate overall score
        overall = sum(scores.values()) / len(scores)
        
        return Assessment(
            score=overall,
            details=scores,
            safety_pass=safety_pass,
            approved=overall >= self.threshold and safety_pass
        )
    
    async def assess_prompt_adherence(
        self,
        frames: List[bytes],
        prompt: str
    ) -> float:
        """Check if video matches prompt."""
        
        response = await self.vision.analyze(
            images=frames,
            prompt=f"""
            Rate how well this video matches the prompt (0-100):
            Prompt: {prompt}
            
            Consider:
            - Are the described elements present?
            - Is the mood/tone correct?
            - Is the action as described?
            
            Return only a number 0-100.
            """
        )
        return float(response)
```

### 6. Timeline Assembler
```python
# Backend/services/video_orchestrator/timeline_assembler.py

class TimelineAssembler:
    """Assemble clips into final video."""
    
    async def assemble(
        self,
        project: VideoProject,
        clips: List[ApprovedClip],
        audio: AudioConfig = None
    ) -> str:
        """Assemble final video from clips."""
        
        # Sort clips by sequence order
        sorted_clips = sorted(clips, key=lambda c: c.sequence_order)
        
        # Create FFmpeg filter chain
        filter_chain = self.build_filter_chain(sorted_clips)
        
        # Add transitions
        filter_chain = self.add_transitions(filter_chain, "crossfade")
        
        # Add audio if provided
        if audio:
            filter_chain = self.add_audio(filter_chain, audio)
        
        # Execute FFmpeg
        output_path = f"/tmp/video_{project.id}.mp4"
        await self.execute_ffmpeg(filter_chain, output_path)
        
        # Apply color grading if style bible specifies
        if project.style_bible.get("color_grade"):
            output_path = await self.apply_color_grade(
                output_path,
                project.style_bible["color_grade"]
            )
        
        return output_path
    
    async def execute_ffmpeg(
        self,
        filter_chain: str,
        output_path: str
    ):
        """Execute FFmpeg command."""
        cmd = f"ffmpeg -y {filter_chain} {output_path}"
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
```

---

## Implementation Phases

### Phase 1: Database & Models (Days 1-2)
| Task | Effort |
|------|--------|
| Database migration | 4h |
| Pydantic models | 4h |
| Basic CRUD API | 6h |

### Phase 2: Director & Crafter (Days 3-5)
| Task | Effort |
|------|--------|
| Director Service | 8h |
| Scene Crafter | 6h |
| Style/Character bibles | 4h |
| API endpoints | 4h |

### Phase 3: Providers (Days 6-10)
| Task | Effort |
|------|--------|
| Provider interface | 4h |
| Sora provider (Safari) | 8h |
| Runway provider | 6h |
| Kling provider | 6h |
| Provider router | 4h |
| Quota management | 4h |

### Phase 4: Assessment & Repair (Days 11-14)
| Task | Effort |
|------|--------|
| Assessor Service | 8h |
| Vision API integration | 4h |
| Repair loop logic | 6h |
| Retry strategies | 4h |

### Phase 5: Timeline & UI (Days 15-20)
| Task | Effort |
|------|--------|
| Timeline Assembler | 8h |
| FFmpeg integration | 6h |
| Audio sync | 4h |
| Storyboard UI | 12h |
| Project dashboard | 8h |

---

## Files to Create

```
Backend/services/video_orchestrator/
├── __init__.py
├── director_service.py
├── scene_crafter.py
├── provider_router.py
├── assessor_service.py
├── timeline_assembler.py
├── repair_service.py
├── models.py
└── providers/
    ├── __init__.py
    ├── base_provider.py
    ├── sora_provider.py
    ├── runway_provider.py
    └── kling_provider.py

Backend/api/endpoints/video_orchestrator.py

dashboard/app/(dashboard)/video-studio/
├── page.tsx                    # Project list
├── new/page.tsx                # Create project
├── [projectId]/page.tsx        # Project detail
├── [projectId]/storyboard/page.tsx
├── [projectId]/timeline/page.tsx
└── components/
    ├── ScriptEditor.tsx
    ├── ClipPlanList.tsx
    ├── StoryboardView.tsx
    ├── TimelineEditor.tsx
    ├── ProviderStatus.tsx
    ├── AssessmentCard.tsx
    └── StyleBibleEditor.tsx
```

---

## Success Criteria

- [ ] Script → shot list in <30 seconds
- [ ] Multi-provider fallback working
- [ ] Assessment accuracy >85%
- [ ] Repair loop reduces failures by 50%
- [ ] Final assembly in <5 minutes
- [ ] Character consistency across clips

---

*Document created: February 1, 2026*
