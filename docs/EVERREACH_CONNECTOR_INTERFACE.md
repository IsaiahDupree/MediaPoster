# EverReach/Blend: Connector Interface Specification

## Overview
All platform connectors implement a standardized `SourceAdapter` interface, enabling modular, environment-driven activation.

---

## Core Interface (TypeScript)

```typescript
export type PlatformMetricSnapshot = {
  platform: string;              // 'instagram' | 'facebook' | 'threads' | 'youtube' | ...
  platformPostId: string;
  url?: string;
  snapshotAt: string;            // ISO 8601
  views?: number;
  impressions?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  saves?: number;
  clicks?: number;
  watchTimeSeconds?: number;
  rawPayload?: any;              // Platform-specific extras
};

export type PersonEvent = {
  personId: string;
  channel: string;
  eventType: string;
  platformId?: string;
  contentExcerpt?: string;
  sentiment?: number;
  trafficType: 'organic' | 'paid';
  metadata?: Record<string, any>;
  occurredAt: string;
};

export interface SourceAdapter {
  readonly id: string;           // 'meta', 'youtube', 'tiktok', 'blotato', etc.
  readonly displayName: string;
  
  /**
   * Check if connector is enabled based on ENV and config
   */
  isEnabled(): boolean;
  
  /**
   * List platforms this connector supports
   */
  listSupportedPlatforms(): string[];
  
  /**
   * Fetch metrics for a content variant
   */
  fetchMetricsForVariant(variant: ContentVariant): Promise<PlatformMetricSnapshot[]>;
  
  /**
   * Optional: Publish a content variant to platform
   */
  publishVariant?(variant: ContentVariant): Promise<{
    url: string;
    platformPostId: string;
  }>;
  
  /**
   * Optional: Fetch person events (comments, likes, etc.)
   */
  fetchPersonEvents?(params: {
    platform: string;
    since?: string;
    until?: string;
  }): Promise<PersonEvent[]>;
  
  /**
   * Optional: Health check
   */
  healthCheck?(): Promise<{ status: 'ok' | 'error'; message?: string }>;
}
```

---

## Implementation Examples

### Meta Connector

```typescript
export class MetaAdapter implements SourceAdapter {
  readonly id = 'meta';
  readonly displayName = 'Meta (FB/IG/Threads)';
  
  private config: {
    appId?: string;
    appSecret?: string;
    pageAccessToken?: string;
  };
  
  constructor() {
    this.config = {
      appId: process.env.META_APP_ID,
      appSecret: process.env.META_APP_SECRET,
      pageAccessToken: process.env.META_PAGE_ACCESS_TOKEN,
    };
  }
  
  isEnabled(): boolean {
    return Boolean(
      (process.env.APP_MODE === 'meta_only' || process.env.APP_MODE === 'full_stack') &&
      this.config.appId &&
      this.config.pageAccessToken
    );
  }
  
  listSupportedPlatforms(): string[] {
    return ['facebook', 'instagram', 'threads'];
  }
  
  async fetchMetricsForVariant(variant: ContentVariant): Promise<PlatformMetricSnapshot[]> {
    // Call Meta Graph API for insights
    // Return standardized snapshot
  }
  
  async publishVariant(variant: ContentVariant): Promise<{ url: string; platformPostId: string }> {
    // Post to Graph API
  }
  
  async fetchPersonEvents(params: any): Promise<PersonEvent[]> {
    // Fetch comments, reactions, shares from Graph API
    // Map to PersonEvent[]
  }
}
```

### Blotato Connector

```typescript
export class BlotatoAdapter implements SourceAdapter {
  readonly id = 'blotato';
  readonly displayName = 'Blotato (Multi-Platform)';
  
  private apiKey?: string;
  
  constructor() {
    this.apiKey = process.env.BLOTATO_API_KEY;
  }
  
  isEnabled(): boolean {
    return Boolean(this.apiKey);
  }
  
  listSupportedPlatforms(): string[] {
    return [
      'instagram', 'tiktok', 'youtube', 'linkedin', 'twitter',
      'facebook', 'pinterest', 'threads', 'bluesky'
    ];
  }
  
  async fetchMetricsForVariant(variant: ContentVariant): Promise<PlatformMetricSnapshot[]> {
    // If Blotato exposes metrics endpoint, call it
    // Otherwise return empty array (post-only mode)
  }
  
  async publishVariant(variant: ContentVariant): Promise<{ url: string; platformPostId: string }> {
    // POST to /v2/media (upload)
    // POST to /v2/posts (publish)
    // Return platform_post_id and URL if available
  }
}
```

### YouTube Connector

```typescript
export class YouTubeAdapter implements SourceAdapter {
  readonly id = 'youtube';
  readonly displayName = 'YouTube Data API';
  
  private credentials?: any;
  
  constructor() {
    this.credentials = process.env.GOOGLE_APPLICATION_CREDENTIALS
      ? JSON.parse(fs.readFileSync(process.env.GOOGLE_APPLICATION_CREDENTIALS, 'utf-8'))
      : null;
  }
  
  isEnabled(): boolean {
    return Boolean(
      (process.env.APP_MODE === 'full_stack') &&
      this.credentials
    );
  }
  
  listSupportedPlatforms(): string[] {
    return ['youtube'];
  }
  
  async fetchMetricsForVariant(variant: ContentVariant): Promise<PlatformMetricSnapshot[]> {
    // Call YouTube Analytics API
    // Return views, watch_time, likes, comments, etc.
  }
}
```

---

## Adapter Registry

```typescript
export class AdapterRegistry {
  private adapters: Map<string, SourceAdapter> = new Map();
  
  register(adapter: SourceAdapter) {
    this.adapters.set(adapter.id, adapter);
  }
  
  getEnabledAdapters(): SourceAdapter[] {
    return Array.from(this.adapters.values()).filter(a => a.isEnabled());
  }
  
  getAdapterById(id: string): SourceAdapter | undefined {
    return this.adapters.get(id);
  }
  
  getAllPlatforms(): string[] {
    return Array.from(new Set(
      this.getEnabledAdapters()
        .flatMap(a => a.listSupportedPlatforms())
    ));
  }
}

// Bootstrap
const registry = new AdapterRegistry();
registry.register(new MetaAdapter());
registry.register(new BlotatoAdapter());
registry.register(new YouTubeAdapter());
registry.register(new TikTokAdapter());
registry.register(new LinkedInAdapter());
registry.register(new LocalCSVAdapter());

export default registry;
```

---

## App Mode Configuration

```typescript
type AppMode = 'meta_only' | 'full_stack' | 'local_lite' | 'blotato_only';

const MODE_CONFIG: Record<AppMode, { allowedAdapters: string[] }> = {
  meta_only: { allowedAdapters: ['meta'] },
  blotato_only: { allowedAdapters: ['blotato'] },
  full_stack: { allowedAdapters: ['meta', 'youtube', 'tiktok', 'blotato', 'linkedin', 'twitter'] },
  local_lite: { allowedAdapters: ['local-csv'] },
};

export function getAppMode(): AppMode {
  return (process.env.APP_MODE as AppMode) || 'full_stack';
}

export function isAdapterAllowed(adapterId: string): boolean {
  const mode = getAppMode();
  return MODE_CONFIG[mode].allowedAdapters.includes(adapterId);
}
```

---

## Environment Variables

```bash
# App Mode
APP_MODE=meta_only|blotato_only|full_stack|local_lite

# Meta Connector
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_PAGE_ACCESS_TOKEN=your_long_lived_token

# Blotato
BLOTATO_API_KEY=blt_xxxxx

# YouTube
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# LinkedIn
LINKEDIN_CLIENT_ID=xxxxx
LINKEDIN_CLIENT_SECRET=xxxxx

# TikTok
TIKTOK_CLIENT_KEY=xxxxx
TIKTOK_CLIENT_SECRET=xxxxx

# RapidAPI (Enrichment)
RAPIDAPI_KEY=xxxxx

# OpenAI (Sentiment/Briefs)
OPENAI_API_KEY=sk-xxxxx
```

---

## Usage Pattern

```typescript
import registry from './adapters/registry';

async function syncMetrics(contentId: string) {
  const variants = await db.getVariantsByContentId(contentId);
  const adapters = registry.getEnabledAdapters();
  
  for (const variant of variants) {
    const adapter = adapters.find(a => 
      a.listSupportedPlatforms().includes(variant.platform)
    );
    
    if (!adapter) {
      console.warn(`No adapter for platform: ${variant.platform}`);
      continue;
    }
    
    try {
      const snapshots = await adapter.fetchMetricsForVariant(variant);
      await db.insertMetrics(snapshots);
    } catch (error) {
      console.error(`Metrics fetch failed for ${variant.platform}:`, error);
    }
  }
}
```
