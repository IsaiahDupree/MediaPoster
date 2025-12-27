# Formats System - Clips Studio

> Parameterized, renderable video formats that can be regenerated with fresh data on demand.

## Overview

The Formats system enables dynamic video generation through reusable templates. Unlike static presets, formats are **data-driven blueprints** that can pull fresh data from multiple sources and compile into renderable video properties.

## Key Concepts

### Format Definition
A format is a JSON blueprint that defines:
- **Composition** - Remotion composition ID, resolution, FPS, duration
- **Data Sources** - Where to fetch dynamic data (Supabase, APIs, local libraries)
- **Bindings** - How data maps to render props (with transforms)
- **Quality Gates** - Validation rules before/after rendering
- **Variants** - Platform-specific versions (9:16, 1:1, etc.)

### Run
Each execution of a format creates a **run** that:
1. Resolves data sources with current data
2. Applies bindings to create render props
3. Validates against quality gates
4. Triggers Remotion rendering
5. Stores artifacts (voice, video, captions, thumbnails)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Format Def    │────▶│    Compiler     │────▶│  Render Props   │
│   (JSON)        │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Sources   │────▶│   Resolved      │────▶│  Quality Gates  │
│  (Supabase,API) │     │   Inputs        │     │  (Pre-render)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Artifacts     │◀────│    Remotion     │◀────│  Quality Gates  │
│   (Storage)     │     │    Render       │     │  (Post-render)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `formats` | Format definitions with JSON schema |
| `format_runs` | Execution history for each run |
| `run_artifacts` | Generated files (voice, video, captions) |
| `quality_profiles` | Reusable quality gate configurations |
| `format_triggers` | Scheduled/event-based triggers |

### Key Fields

**formats**
```sql
id TEXT PRIMARY KEY,
name TEXT NOT NULL,
description TEXT,
status TEXT CHECK (status IN ('draft', 'active', 'archived')),
version TEXT,
definition_json JSONB,  -- Full format definition
quality_profile_id TEXT REFERENCES quality_profiles(id)
```

**format_runs**
```sql
id UUID PRIMARY KEY,
format_id TEXT REFERENCES formats(id),
status TEXT CHECK (status IN ('queued', 'running', 'failed', 'succeeded', 'published')),
trigger_type TEXT CHECK (trigger_type IN ('manual', 'schedule', 'webhook', 'event')),
params_json JSONB,           -- Input parameters
resolved_inputs_json JSONB,  -- Data source results
render_props_json JSONB,     -- Final props for Remotion
error_json JSONB
```

## Format Definition Schema

```json
{
  "id": "dev_vlog_meme_v1",
  "name": "Dev Vlog + Memes",
  "version": "1.0.0",
  "status": "active",
  
  "composition": {
    "remotionCompositionId": "DevVlogMeme",
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "defaultDurationSec": 55,
    "variantSets": [
      { "id": "shorts_9x16", "label": "Shorts", "width": 1080, "height": 1920, "maxDurationSec": 60 },
      { "id": "square_1x1", "label": "Square", "width": 1080, "height": 1080, "maxDurationSec": 60 }
    ]
  },
  
  "defaults": {
    "params": {
      "hookIntensity": 0.9,
      "captionStyle": "bold_pop"
    },
    "providers": {
      "tts": { "provider": "huggingface", "model": "IndexTTS2" },
      "music": { "provider": "library" },
      "visuals": { "provider": "local" }
    },
    "qualityProfileId": "qp_shortform_v1"
  },
  
  "dataSources": [
    { "id": "trendCluster", "type": "supabase_query", "queryName": "topTrendCluster" },
    { "id": "memes", "type": "local_library", "libraryId": "meme_bank", "filter": { "limit": 20 } }
  ],
  
  "bindings": [
    { "target": "topic", "from": "trendCluster.name", "required": true },
    { "target": "script.hook", "from": "trendCluster.angles[0].hook" },
    { "target": "visuals.memes", "from": "memes.items" }
  ],
  
  "gates": [
    { "id": "max_duration", "type": "duration", "level": "fail", "config": { "maxSec": 60 } }
  ]
}
```

## Data Sources

### Supabase Query
```json
{
  "id": "trendCluster",
  "type": "supabase_query",
  "queryName": "topTrendCluster",
  "params": { "windowHours": 24 }
}
```

### HTTP API
```json
{
  "id": "newsData",
  "type": "http_api",
  "url": "https://api.example.com/news?topic={{params.topic}}",
  "method": "GET",
  "headers": { "Authorization": "Bearer {{env.API_KEY}}" }
}
```

### Local Library
```json
{
  "id": "memes",
  "type": "local_library",
  "libraryId": "meme_bank",
  "filter": { "limit": 20, "tags": ["tech"] }
}
```

## Bindings & Transforms

### Basic Binding
```json
{ "target": "topic", "from": "trendCluster.name", "required": true }
```

### With Transform
```json
{
  "target": "script.segments",
  "from": "trendCluster.angles",
  "transform": {
    "type": "map",
    "mapTemplate": {
      "id": "{{item.id}}",
      "text": "{{item.script}}",
      "intent": "{{item.intent}}"
    }
  }
}
```

### Transform Types

| Type | Description |
|------|-------------|
| `pick` | Extract nested path: `{ "type": "pick", "path": "data.items[0]" }` |
| `map` | Transform array items with template |
| `template` | String interpolation: `{ "type": "template", "template": "Hello {{value}}" }` |
| `coerce` | Type conversion: `{ "type": "coerce", "to": "number" }` |
| `default` | Fallback value: `{ "type": "default", "value": "Untitled" }` |

## Quality Gates

### Gate Types

| Type | Config | Description |
|------|--------|-------------|
| `required_fields` | `{ "paths": ["topic", "script.segments"] }` | Ensure fields exist |
| `duration` | `{ "maxSec": 60 }` | Video length limit |
| `captions` | `{ "maxCharsPerLine": 44 }` | Caption length |
| `audio` | `{ "requireVoice": true }` | Voice presence |
| `visual` | `{ "maxOnScreenWords": 12 }` | Text density |

### Gate Levels
- `fail` - Block rendering if not met
- `warn` - Allow but flag issue

## Render Props Contract

The final output passed to Remotion:

```typescript
interface RenderProps {
  topic: string;
  script: {
    title?: string;
    hook?: string;
    segments: Array<{
      id: string;
      text: string;
      t_start_sec?: number;
      t_end_sec?: number;
      intent?: 'hook' | 'explain' | 'joke' | 'cta';
    }>;
  };
  audio: {
    voice_url?: string;
    music_url?: string;
    ducking?: {
      enabled: boolean;
      music_gain_db: number;
    };
  };
  visuals: {
    memes?: Array<{ id: string; url: string }>;
    broll?: Array<{ id: string; url: string }>;
    ugc?: { cutout_url?: string; placement: string };
  };
  style: {
    caption_style: 'bold_pop' | 'clean_subs';
    hook_intensity: number;
    zoom_punch: boolean;
  };
  meta: {
    run_id: string;
    format_id: string;
    variant_id?: string;
  };
}
```

## API Endpoints

### Formats CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/formats/list` | List all formats |
| GET | `/api/formats/{id}` | Get format details |
| POST | `/api/formats/create` | Create new format |
| PUT | `/api/formats/{id}` | Update format |
| DELETE | `/api/formats/{id}` | Archive format |
| POST | `/api/formats/seed-samples` | Seed sample formats |

### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/formats/{id}/run` | Trigger new run |
| GET | `/api/formats/{id}/runs` | List run history |
| GET | `/api/formats/runs/{runId}` | Get run details |
| GET | `/api/formats/runs/{runId}/artifacts` | Get artifacts |

### Quality Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/formats/quality-profiles/list` | List profiles |

## UI Pages

### `/formats` - Format List
- Filter by status (all, active, draft, archived)
- Shows last run status
- Quick run button
- Seed samples button

### `/formats/{id}` - Format Detail
**Tabs:**
- **Overview** - Composition config, defaults, providers, gates
- **Inputs** - Binding table (target → from → transform)
- **Data Sources** - Source configurations
- **Variants** - Platform variants with quick run
- **Triggers** - Scheduled triggers (coming soon)
- **Run History** - Past runs with status

### `/formats/{id}/runs/{runId}` - Run Detail
- Status and timing
- Quality gate results
- Render props JSON
- Resolved inputs JSON
- Artifacts list with download

## Sample Formats

Five pre-built templates included:

1. **Dev Vlog + Memes** - Developer content with meme overlays
2. **AI Explainer** - Educational videos with clear narration
3. **Trend Breakdown** - Quick trending topic analysis
4. **Product Promo** - Product showcase with CTAs
5. **UGC Corner Overlay** - Speaker cutout in corner

Seed them via: `POST /api/formats/seed-samples`

## File Structure

```
Backend/
├── services/formats/
│   ├── __init__.py
│   ├── schema.py          # Pydantic models
│   ├── compiler.py        # Data resolution, binding engine
│   ├── quality_gates.py   # Validation logic
│   └── sample_formats.py  # Template definitions
├── api/endpoints/
│   └── formats.py         # REST API routes

dashboard/app/(dashboard)/formats/
├── page.tsx               # Format list
├── [formatId]/
│   ├── page.tsx           # Format detail
│   └── runs/[runId]/
│       └── page.tsx       # Run detail

supabase/migrations/
└── 20241227000005_formats_system.sql
```

## Usage Example

### 1. Create a Format
```bash
curl -X POST http://localhost:8000/api/formats/create \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my_format",
    "name": "My Custom Format",
    "definition_json": { ... }
  }'
```

### 2. Trigger a Run
```bash
curl -X POST http://localhost:8000/api/formats/my_format/run \
  -H "Content-Type: application/json" \
  -d '{
    "params": { "topic": "AI News" },
    "trigger_type": "manual"
  }'
```

### 3. Check Run Status
```bash
curl http://localhost:8000/api/formats/runs/{run_id}
```

## Future Enhancements

- [ ] Scheduled triggers (cron-based)
- [ ] Event-based triggers (new video analyzed, trend detected)
- [ ] Webhook triggers for external systems
- [ ] A/B testing variants
- [ ] Batch run queuing
- [ ] Run comparison views
