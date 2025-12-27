# Media Factory - System Architecture Diagram

This document contains Mermaid diagrams showing the complete Media Factory system architecture.

---

## Complete System Architecture

```mermaid
graph TB
    %% Input Layer
    Trends[Social Media Trends<br/>Hashtags, Sounds, Topics]
    
    %% Brief Generation Layer
    Trends --> BriefService[Enhanced Brief Service]
    BriefService --> |Cluster Trends| Clusterer[Trend Clusterer]
    BriefService --> |Generate Angles| AngleGen[Angle Generator]
    BriefService --> |Score Briefs| Scorer[Brief Scorer<br/>0-100 Score]
    BriefService --> |Generate Script| ScriptGen[Script Generator]
    
    %% Pipeline Orchestrator
    BriefService --> |Brief + Script| Pipeline[Pipeline Orchestrator]
    
    %% Core Services Layer
    Pipeline --> |Stage 1| BriefStage[Brief Stage]
    Pipeline --> |Stage 2| ScriptStage[Script Stage]
    Pipeline --> |Stage 3| TTSStage[TTS Stage]
    Pipeline --> |Stage 4| MusicStage[Music Stage]
    Pipeline --> |Stage 5| VisualsStage[Visuals Stage]
    Pipeline --> |Stage 6| RemotionStage[Remotion Stage]
    Pipeline --> |Stage 7| PublishStage[Publish Stage]
    
    %% TTS Service
    TTSStage --> TTSWorker[TTS Worker]
    TTSWorker --> TTSAdapter[TTS Adapter]
    TTSAdapter --> |IndexTTS2| HFApi[Hugging Face API]
    TTSWorker --> |voice.wav| RemotionStage
    
    %% Matting Service (optional)
    VisualsStage -.-> |Optional| MattingWorker[Matting Worker]
    MattingWorker --> MattingAdapter[Matting Adapter]
    MattingAdapter --> |RVM| RVMAdapter[RVM Adapter]
    MattingAdapter --> |MediaPipe| MPAdapter[MediaPipe Adapter]
    MattingWorker --> |matted_video.mov| RemotionStage
    
    %% Music Service
    MusicStage --> MusicWorker[Music Worker]
    MusicWorker --> MusicAdapter[Music Adapter]
    MusicAdapter --> |Suno| SunoAdapter[Suno Adapter<br/>Local Files]
    MusicAdapter --> |SoundCloud| SCApi[SoundCloud RapidAPI]
    MusicAdapter --> |Social| SocialApi[Social Platform RapidAPI<br/>TikTok, Instagram]
    MusicWorker --> |music.mp3| RemotionStage
    
    %% Visuals Service
    VisualsStage --> VisualsWorker[Visuals Worker]
    VisualsWorker --> VisualsAdapter[Visuals Adapter]
    VisualsAdapter --> |Meme| MemeAdapter[Meme Adapter<br/>Local + RapidAPI]
    VisualsAdapter --> |B-roll| BrollAdapter[B-roll Adapter<br/>Local + RapidAPI]
    VisualsAdapter --> |UGC| UGCAdapter[UGC Adapter<br/>Local + MediaPoster]
    VisualsWorker --> |broll.mp4, memes.png| RemotionStage
    
    %% Remotion Service
    RemotionStage --> RemotionWorker[Remotion Worker]
    RemotionWorker --> SourceLoader[Source Loader<br/>Multi-Source]
    RemotionWorker --> Composer[Remotion Composer]
    Composer --> |timeline.json| RemotionCLI[Remotion CLI<br/>Node.js]
    RemotionCLI --> |final_video.mp4| PublishStage
    
    %% Publishing Service
    PublishStage --> Publisher[Publishing Service<br/>MediaPoster]
    Publisher --> |YouTube Shorts| YT[YouTube]
    Publisher --> |TikTok| TT[TikTok]
    Publisher --> |Instagram Reels| IG[Instagram]
    
    %% Event Bus (Central)
    EventBus[Event Bus<br/>Central Message Hub]
    TTSWorker <--> EventBus
    MattingWorker <--> EventBus
    MusicWorker <--> EventBus
    VisualsWorker <--> EventBus
    RemotionWorker <--> EventBus
    Pipeline <--> EventBus
    BriefService <--> EventBus
    
    %% Styling
    classDef inputStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef serviceStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef adapterStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef outputStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef eventStyle fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    
    class Trends inputStyle
    class BriefService,Clusterer,AngleGen,Scorer,ScriptGen,Pipeline serviceStyle
    class TTSWorker,MattingWorker,MusicWorker,VisualsWorker,RemotionWorker serviceStyle
    class TTSAdapter,MattingAdapter,MusicAdapter,VisualsAdapter adapterStyle
    class SunoAdapter,SCApi,SocialApi,MemeAdapter,BrollAdapter,UGCAdapter adapterStyle
    class RVMAdapter,MPAdapter adapterStyle
    class Publisher,YT,TT,IG outputStyle
    class EventBus eventStyle
```

---

## Event Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Pipeline
    participant BriefService
    participant TTSWorker
    participant MusicWorker
    participant VisualsWorker
    participant RemotionWorker
    participant Publisher
    participant EventBus
    
    User->>API: POST /api/pipeline/execute
    API->>EventBus: pipeline.requested
    EventBus->>Pipeline: Start execution
    
    Pipeline->>EventBus: pipeline.stage.started (brief)
    EventBus->>BriefService: content.brief.requested
    BriefService->>BriefService: Cluster trends
    BriefService->>BriefService: Generate angles
    BriefService->>BriefService: Score briefs
    BriefService->>EventBus: content.brief.generated
    BriefService->>EventBus: content.brief.script.generated
    EventBus->>Pipeline: Script ready
    
    Pipeline->>EventBus: pipeline.stage.started (tts)
    EventBus->>TTSWorker: tts.requested
    TTSWorker->>TTSWorker: Generate speech
    TTSWorker->>EventBus: tts.completed (voice.wav)
    EventBus->>Pipeline: TTS ready
    
    Pipeline->>EventBus: pipeline.stage.started (music)
    EventBus->>MusicWorker: music.requested
    MusicWorker->>MusicWorker: Search & download
    MusicWorker->>EventBus: music.completed (music.mp3)
    EventBus->>Pipeline: Music ready
    
    Pipeline->>EventBus: pipeline.stage.started (visuals)
    EventBus->>VisualsWorker: visuals.requested (broll)
    VisualsWorker->>VisualsWorker: Search & load
    VisualsWorker->>EventBus: visuals.completed (broll.mp4)
    EventBus->>VisualsWorker: visuals.requested (meme)
    VisualsWorker->>EventBus: visuals.completed (meme.png)
    EventBus->>Pipeline: Visuals ready
    
    Pipeline->>EventBus: pipeline.stage.started (remotion)
    EventBus->>RemotionWorker: remotion.requested
    RemotionWorker->>RemotionWorker: Load sources
    RemotionWorker->>RemotionWorker: Generate timeline
    RemotionWorker->>RemotionWorker: Render video
    RemotionWorker->>EventBus: remotion.completed (video.mp4)
    EventBus->>Pipeline: Video ready
    
    Pipeline->>EventBus: pipeline.stage.started (publish)
    EventBus->>Publisher: publish.requested
    Publisher->>Publisher: Upload to platforms
    Publisher->>EventBus: publish.completed
    EventBus->>Pipeline: Published
    
    Pipeline->>EventBus: pipeline.completed
    EventBus->>API: Pipeline finished
    API->>User: 200 OK (pipeline_id, status)
```

---

## Service Interaction Diagram

```mermaid
graph LR
    subgraph "Input Layer"
        Trends[Trends]
    end
    
    subgraph "Intelligence Layer"
        Brief[Brief Service]
        Score[Scoring<br/>0-100]
        Cluster[Clustering]
        Angle[Angle Gen]
    end
    
    subgraph "Core Services"
        TTS[TTS Service]
        Matting[Matting Service]
        Remotion[Remotion Service]
    end
    
    subgraph "Asset Services"
        Music[Music Service]
        Visuals[Visuals Service]
    end
    
    subgraph "Orchestration"
        Pipeline[Pipeline Orchestrator]
    end
    
    subgraph "Output Layer"
        Publish[Publishing Service]
        Platforms[YouTube, TikTok, Instagram]
    end
    
    subgraph "Event Bus"
        EB[Event Bus<br/>47 Topics]
    end
    
    Trends --> Brief
    Brief --> Score
    Brief --> Cluster
    Brief --> Angle
    Brief --> Pipeline
    
    Pipeline --> TTS
    Pipeline --> Music
    Pipeline --> Visuals
    Pipeline --> Remotion
    
    TTS --> Remotion
    Music --> Remotion
    Visuals --> Remotion
    Matting -.-> Remotion
    
    Remotion --> Publish
    Publish --> Platforms
    
    TTS <--> EB
    Matting <--> EB
    Music <--> EB
    Visuals <--> EB
    Remotion <--> EB
    Pipeline <--> EB
    Brief <--> EB
    
    style EB fill:#fff9c4,stroke:#f57f17,stroke-width:3px
    style Pipeline fill:#e1f5ff,stroke:#01579b,stroke-width:2px
```

---

## Adapter Pattern Diagram

```mermaid
graph TB
    subgraph "TTS Service"
        TTSWorker[TTS Worker]
        TTSBase[TTS Adapter Base]
        IndexTTS2[IndexTTS2 Adapter]
        FutureTTS[Future: ElevenLabs, Coqui]
    end
    
    subgraph "Matting Service"
        MattingWorker[Matting Worker]
        MattingBase[Matting Adapter Base]
        RVM[RVM Adapter]
        MediaPipe[MediaPipe Adapter]
        FutureMat[Future: SAM 2, BackgroundMattingV2]
    end
    
    subgraph "Music Service"
        MusicWorker[Music Worker]
        MusicBase[Music Adapter Base]
        Suno[Suno Adapter]
        SoundCloud[SoundCloud Adapter]
        Social[Social Platform Adapter]
    end
    
    subgraph "Visuals Service"
        VisualsWorker[Visuals Worker]
        VisualsBase[Visuals Adapter Base]
        Meme[Meme Adapter]
        Broll[B-roll Adapter]
        UGC[UGC Adapter]
    end
    
    TTSWorker --> TTSBase
    TTSBase --> IndexTTS2
    TTSBase -.-> FutureTTS
    
    MattingWorker --> MattingBase
    MattingBase --> RVM
    MattingBase --> MediaPipe
    MattingBase -.-> FutureMat
    
    MusicWorker --> MusicBase
    MusicBase --> Suno
    MusicBase --> SoundCloud
    MusicBase --> Social
    
    VisualsWorker --> VisualsBase
    VisualsBase --> Meme
    VisualsBase --> Broll
    VisualsBase --> UGC
    
    style TTSBase fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style MattingBase fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style MusicBase fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style VisualsBase fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

## Data Flow Diagram

```mermaid
flowchart TD
    Start([Trend Discovery]) --> Trends[Trend Cards<br/>Hashtags, Sounds, Topics]
    
    Trends --> Cluster[Cluster Trends<br/>Cross-Platform]
    Cluster --> Angles[Generate Angles<br/>8-20 per cluster]
    Angles --> Score[Score Angles<br/>0-100]
    
    Score --> Filter{Score ≥ 70?<br/>or ≥60 strategic?}
    Filter -->|No| Reject[Reject Brief]
    Filter -->|Yes| Brief[Enhanced Brief]
    
    Brief --> Script[Generate Script<br/>script.json]
    
    Script --> TTS[Generate TTS<br/>voice.wav + timestamps]
    Script --> Music[Select Music<br/>trending + mood match]
    Script --> Visuals[Select Visuals<br/>B-roll + memes]
    
    TTS --> Remotion[Remotion Composition]
    Music --> Remotion
    Visuals --> Remotion
    
    Remotion --> Timeline[Generate timeline.json]
    Timeline --> Render[Render Video<br/>Remotion CLI]
    Render --> Video[final_video.mp4]
    
    Video --> Publish[Publish to Platforms]
    Publish --> YT[YouTube Shorts]
    Publish --> TT[TikTok]
    Publish --> IG[Instagram Reels]
    
    YT --> Analytics[Analytics Collection]
    TT --> Analytics
    IG --> Analytics
    
    style Filter fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style Reject fill:#ffebee,stroke:#c62828,stroke-width:2px
    style Brief fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Video fill:#e1f5ff,stroke:#01579b,stroke-width:2px
```

---

## Component Dependencies

```mermaid
graph TD
    subgraph "External Dependencies"
        HF[Hugging Face API<br/>IndexTTS2]
        RapidAPI[RapidAPI<br/>SoundCloud, Social Platforms]
        OpenAI[OpenAI API<br/>Brief Generation]
        RemotionProj[Remotion Project<br/>Node.js/React]
    end
    
    subgraph "Media Factory Services"
        TTS[TTS Service]
        Matting[Matting Service]
        Music[Music Service]
        Visuals[Visuals Service]
        Brief[Brief Service]
        Remotion[Remotion Service]
    end
    
    subgraph "Infrastructure"
        EventBus[Event Bus]
        Database[(PostgreSQL<br/>Supabase)]
        Storage[File Storage<br/>Local/S3]
    end
    
    TTS --> HF
    Music --> RapidAPI
    Brief --> OpenAI
    Remotion --> RemotionProj
    
    TTS --> EventBus
    Matting --> EventBus
    Music --> EventBus
    Visuals --> EventBus
    Brief --> EventBus
    Remotion --> EventBus
    
    Brief --> Database
    TTS --> Storage
    Matting --> Storage
    Music --> Storage
    Visuals --> Storage
    Remotion --> Storage
    
    style HF fill:#ffebee,stroke:#c62828,stroke-width:2px
    style RapidAPI fill:#ffebee,stroke:#c62828,stroke-width:2px
    style OpenAI fill:#ffebee,stroke:#c62828,stroke-width:2px
    style RemotionProj fill:#ffebee,stroke:#c62828,stroke-width:2px
    style EventBus fill:#fff9c4,stroke:#f57f17,stroke-width:3px
```

---

## Scoring System Flow

```mermaid
flowchart TD
    TrendCard[Trend Card<br/>Hashtag, Sound, Topic] --> Scorer[Brief Scorer]
    
    Scorer --> Velocity[Velocity Score<br/>0-25<br/>Views/hour, Shares, Comments]
    Scorer --> Intent[Intent Score<br/>0-20<br/>How do I, What tool, Template]
    Scorer --> ProductFit[Product Fit Score<br/>0-25<br/>Service/Product mentions]
    Scorer --> Diff[Differentiation Score<br/>0-15<br/>Unique lens potential]
    Scorer --> Feasibility[Feasibility Score<br/>0-15<br/>Production speed]
    
    Velocity --> Total[Total Score<br/>0-100]
    Intent --> Total
    ProductFit --> Total
    Diff --> Total
    Feasibility --> Total
    
    Total --> Check{Score ≥ 70?<br/>or ≥60 strategic?}
    Check -->|Yes| Approve[Approve Brief<br/>Generate Script]
    Check -->|No| Reject[Reject Brief]
    
    style Total fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style Check fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style Approve fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Reject fill:#ffebee,stroke:#c62828,stroke-width:2px
```

---

## API Endpoint Structure

```mermaid
graph TB
    API[FastAPI Application<br/>/api]
    
    API --> TTSAPI[TTS Endpoints<br/>/api/tts]
    API --> MattingAPI[Matting Endpoints<br/>/api/matting]
    API --> RemotionAPI[Remotion Endpoints<br/>/api/remotion]
    API --> PipelineAPI[Pipeline Endpoints<br/>/api/pipeline]
    API --> MusicAPI[Music Endpoints<br/>/api/music]
    API --> VisualsAPI[Visuals Endpoints<br/>/api/visuals]
    
    TTSAPI --> TTSGen[POST /generate]
    TTSAPI --> TTSStatus[GET /status/{job_id}]
    TTSAPI --> TTSModels[GET /models]
    
    MattingAPI --> MattingProcess[POST /process]
    MattingAPI --> MattingStatus[GET /status/{job_id}]
    MattingAPI --> MattingModels[GET /models]
    
    RemotionAPI --> RemotionRender[POST /render]
    RemotionAPI --> RemotionStatus[GET /status/{job_id}]
    RemotionAPI --> RemotionSources[GET /source-types]
    
    PipelineAPI --> PipelineExec[POST /execute]
    PipelineAPI --> PipelineStatus[GET /status/{pipeline_id}]
    
    MusicAPI --> MusicRequest[POST /request]
    MusicAPI --> MusicSources[GET /sources]
    
    VisualsAPI --> VisualsRequest[POST /request]
    VisualsAPI --> VisualsTypes[GET /types]
    VisualsAPI --> VisualsSources[GET /sources]
    
    style API fill:#e1f5ff,stroke:#01579b,stroke-width:3px
```

---

*These diagrams show the complete Media Factory system architecture, data flow, and component interactions.*

