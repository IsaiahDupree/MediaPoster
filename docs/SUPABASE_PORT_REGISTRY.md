# Supabase Port Registry

**Last Updated:** 2026-01-31

This document tracks Supabase port assignments across all projects to prevent conflicts when running multiple instances locally.

## Port Assignment Strategy

Each project gets a unique port range:
- **Base + 20** = Shadow port
- **Base + 21** = API port  
- **Base + 22** = DB port
- **Base + 23** = Studio port
- **Base + 24** = Inbucket port
- **Base + 27** = Analytics port
- **Base + 29** = Pooler port
- **8x83** = Inspector port (unique per project)

## Master Port Registry

| Project | Base | API | DB | Shadow | Pooler | Studio | Inbucket | Analytics | Inspector |
|---------|------|-----|-----|--------|--------|--------|----------|-----------|-----------|
| **MediaPoster** | 543xx | 54321 | 54322 | 54320 | 54329 | 54323 | 54324 | 54327 | 8083 |
| **gap-radar** | 544xx | 54421 | 54422 | 54420 | 54429 | 54423 | 54424 | 54427 | 8183 |
| **Riona** | 545xx | 54521 | 54522 | 54520 | 54529 | 54523 | 54524 | 54527 | 8283 |
| **everreach_backend_2** | 546xx | 54621 | 54622 | 54620 | 54629 | 54623 | 54624 | 54627 | 8383 |
| **autonomous-coding-dashboard** | 547xx | 54721 | 54722 | 54720 | 54729 | 54723 | 54724 | 54727 | 8483 |
| **Portal28** | 548xx | 54821 | 54822 | 54820 | 54829 | 54823 | 54824 | 54827 | 8583 |
| **KindLetters** | 549xx | 54921 | 54922 | 54920 | 54929 | 54923 | 54924 | 54927 | 8683 |
| **waitlist-lab** | 550xx | 55021 | 55022 | 55020 | 55029 | 55023 | 55024 | 55027 | 8783 |
| **everreach_frontend** | 551xx | 55121 | 55122 | 55120 | 55129 | 55123 | 55124 | 55127 | 8883 |

## Connection Strings

### MediaPoster (This Project)
```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
STUDIO_URL=http://127.0.0.1:54323
```

### gap-radar
```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54422/postgres
SUPABASE_URL=http://127.0.0.1:54421
STUDIO_URL=http://127.0.0.1:54423
```

### Riona
```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54522/postgres
SUPABASE_URL=http://127.0.0.1:54521
STUDIO_URL=http://127.0.0.1:54523
```

## Adding a New Project

If adding a new Supabase project, use the next available base (552xx):

```toml
# supabase/config.toml
project_id = "new-project"

[api]
port = 55221

[db]
port = 55222
shadow_port = 55220

[db.pooler]
port = 55229

[studio]
port = 55223

[inbucket]
port = 55224

[analytics]
port = 55227

[edge_runtime]
inspector_port = 8983
```

## Running Multiple Projects

You can now run multiple Supabase instances simultaneously:

```bash
# Terminal 1 - MediaPoster
cd ~/Documents/Software/MediaPoster && supabase start

# Terminal 2 - gap-radar  
cd ~/Documents/Software/WhatsCurrentlyInTheMarket/gap-radar && supabase start

# Terminal 3 - Riona
cd ~/Documents/Software/Riona && supabase start
```

All will run without port conflicts.
