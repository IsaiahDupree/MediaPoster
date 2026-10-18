# AI-Assisted Curation System PRD

## Overview

This PRD defines an AI-assisted curation system designed to dramatically improve the efficiency of human content review. With thousands of videos in the content library, manual curation is time-consuming. This system uses AI analysis to automate decisions where confidence is high, flag duplicates for bulk deletion, and provide bulk action tools for efficient human review.

## Problem Statement

- **Volume**: 8,000+ media files in the iPhone Import folder require curation
- **Time**: Manual review of each video is unsustainable
- **Quality**: Duplicate content and negative sentiment videos waste reviewer time
- **Efficiency**: Current curation flow is one-by-one, lacking bulk operations

## Goals

1. **Full Analysis Coverage**: Ensure all videos have complete AI analysis (transcription, sentiment, scoring)
2. **Duplicate Detection**: Identify and enable bulk deletion of videos with duplicate transcripts
3. **Auto-Curation**: Automatically approve/deny content based on sentiment analysis
4. **Bulk Tools**: Provide efficient bulk operations for human reviewers
5. **Quality Gate**: Ensure narrative builder only uses approved, high-quality content

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Videos analyzed | ~30% | 100% |
| Curation time per video | 30s | 5s (with bulk ops) |
| Auto-curated content | 0% | 40-60% |
| Duplicate videos removed | 0 | All identified |

---

## Feature Requirements

### Phase 1: Full Video Analysis

**Objective**: Analyze all unanalyzed videos in the media library.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P1-001 | Batch analysis endpoint to queue all unanalyzed videos | High |
| P1-002 | Progress tracking for batch analysis jobs | High |
| P1-003 | Dashboard widget showing analysis coverage | Medium |
| P1-004 | Automatic sentiment scoring for all transcripts | High |
| P1-005 | Store sentiment score (-1 to 1) and label (negative/neutral/positive) | High |

#### Sentiment Analysis Schema

```sql
ALTER TABLE media ADD COLUMN IF NOT EXISTS sentiment_score DECIMAL(4,3);
ALTER TABLE media ADD COLUMN IF NOT EXISTS sentiment_label VARCHAR(20);
-- sentiment_label: 'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
```

#### API Endpoints

```
POST /api/analysis/batch-analyze-all
  - Queues all unanalyzed videos for analysis
  - Returns job_id for tracking

GET /api/analysis/batch-status/{job_id}
  - Returns progress: { total, completed, failed, current_file }

GET /api/analysis/coverage-stats
  - Returns: { total_media, analyzed, unanalyzed, with_transcript, with_sentiment }
```

---

### Phase 2: Duplicate Transcript Detection & Deletion

**Objective**: Identify videos with duplicate/near-duplicate transcripts and enable bulk deletion.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P2-001 | Transcript similarity detection using fuzzy matching | High |
| P2-002 | Group duplicates by similarity threshold (>90% similar) | High |
| P2-003 | UI to review duplicate groups with preview | High |
| P2-004 | Bulk delete button that removes actual files from iPhone Import folder | Critical |
| P2-005 | Confirmation modal before deletion with file count | Critical |
| P2-006 | Keep "best" version option (highest score, best resolution) | Medium |
| P2-007 | Deletion audit log | Medium |

#### Duplicate Detection Algorithm

```python
def find_duplicates(threshold=0.9):
    """
    1. Get all videos with transcripts
    2. Use fuzzy matching (rapidfuzz) to compare transcripts
    3. Group videos with similarity > threshold
    4. Return groups sorted by size (largest first)
    """
```

#### API Endpoints

```
GET /api/curation/duplicates
  - Returns duplicate groups: [{ group_id, videos: [...], similarity_score }]
  
POST /api/curation/duplicates/delete
  - Body: { group_id, keep_video_id, delete_video_ids: [...] }
  - PERMANENTLY deletes files from disk
  - Removes from database
  - Returns: { deleted_count, freed_bytes }

POST /api/curation/duplicates/bulk-delete
  - Body: { groups: [{ group_id, keep_video_id }] }
  - Processes multiple groups at once
```

#### Safety Requirements

- **CRITICAL**: Require explicit confirmation for file deletion
- **CRITICAL**: Log all deletions with file paths for recovery reference
- **CRITICAL**: Verify file exists before attempting deletion
- Show total disk space to be freed before confirming

---

### Phase 3: Sentiment-Based Auto-Curation

**Objective**: Automatically approve/deny content based on sentiment analysis.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P3-001 | Auto-deny videos with very negative sentiment (< -0.5) | High |
| P3-002 | Auto-approve videos with very positive sentiment (> 0.7) | High |
| P3-003 | Configurable thresholds in settings | Medium |
| P3-004 | Manual override capability for auto-decisions | High |
| P3-005 | Dashboard showing auto-curation statistics | Medium |
| P3-006 | Exclusion rules (e.g., always review videos > 60s) | Low |

#### Auto-Curation Rules

```python
AUTO_CURATION_RULES = {
    "auto_deny": {
        "sentiment_below": -0.5,
        "reason": "Negative sentiment content"
    },
    "auto_approve": {
        "sentiment_above": 0.7,
        "min_score": 60,  # Also needs decent pre-social score
        "reason": "High positive sentiment"
    },
    "require_review": {
        "sentiment_range": (-0.5, 0.7),
        "reason": "Sentiment in review range"
    }
}
```

#### API Endpoints

```
POST /api/curation/auto-curate
  - Runs auto-curation on all pending content
  - Returns: { auto_approved, auto_denied, require_review }

GET /api/curation/auto-curate/preview
  - Preview what would be auto-curated without making changes

PUT /api/curation/settings/auto-curate
  - Update thresholds and rules
```

---

### Phase 4: Bulk Curation Tools

**Objective**: Provide efficient bulk operations for human reviewers.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P4-001 | Bulk approve selected videos | High |
| P4-002 | Bulk deny selected videos | High |
| P4-003 | Bulk approve by filter (e.g., all with score > 80) | High |
| P4-004 | Bulk deny by filter (e.g., all < 30s duration) | High |
| P4-005 | Select all / deselect all in curation view | High |
| P4-006 | Filter presets (e.g., "High confidence", "Needs review") | Medium |
| P4-007 | Keyboard shortcuts for rapid curation | Medium |
| P4-008 | Undo last bulk action | Low |

#### Bulk Action Filters

```typescript
interface BulkFilter {
  sentiment_min?: number;
  sentiment_max?: number;
  score_min?: number;
  score_max?: number;
  duration_min?: number;
  duration_max?: number;
  media_type?: 'video' | 'image';
  has_transcript?: boolean;
}
```

#### API Endpoints

```
POST /api/curation/bulk-approve
  - Body: { media_ids: [...] } OR { filter: BulkFilter }
  - Returns: { approved_count }

POST /api/curation/bulk-deny
  - Body: { media_ids: [...] } OR { filter: BulkFilter }
  - Returns: { denied_count }

GET /api/curation/filter-preview
  - Body: { filter: BulkFilter }
  - Returns: { count, sample_ids: [...] }
```

---

### Phase 5: Narrative Builder Integration

**Objective**: Ensure narrative builder only uses approved content.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P5-001 | Narrative builder queries only `curation_status = 'approved'` | Critical |
| P5-002 | Warning if approved content pool is too small | Medium |
| P5-003 | Curation status filter in content selection UI | Medium |
| P5-004 | Stats showing approved content by category/theme | Low |

#### Database Query Update

```sql
-- Narrative builder content selection
SELECT * FROM media 
WHERE curation_status = 'approved'
  AND pre_social_score >= :min_score
ORDER BY pre_social_score DESC;
```

---

## UI/UX Requirements

### Curation Dashboard Enhancements

1. **Analysis Progress Widget**
   - Shows: X of Y videos analyzed (Z%)
   - "Analyze All" button
   - Estimated time remaining

2. **Duplicate Detection Panel**
   - Card showing duplicate groups found
   - "Review Duplicates" button → opens duplicate manager
   - Total space recoverable

3. **Auto-Curation Stats**
   - Pie chart: Auto-approved / Auto-denied / Pending review
   - "Run Auto-Curate" button
   - Last run timestamp

4. **Bulk Actions Toolbar**
   - Selection count
   - "Approve Selected" / "Deny Selected" buttons
   - Filter dropdown with presets
   - "Apply Filter" for bulk operations

### Duplicate Manager View

```
┌─────────────────────────────────────────────────────────────┐
│ Duplicate Groups (15 found)              [Delete All Dups] │
├─────────────────────────────────────────────────────────────┤
│ Group 1 (3 videos) - 95% similar                           │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│ │ [thumb] │ │ [thumb] │ │ [thumb] │                       │
│ │ ★ KEEP  │ │ DELETE  │ │ DELETE  │                       │
│ │ 1080p   │ │ 720p    │ │ 720p    │                       │
│ │ Score:85│ │ Score:72│ │ Score:68│                       │
│ └─────────┘ └─────────┘ └─────────┘                       │
│                                          [Confirm Delete] │
├─────────────────────────────────────────────────────────────┤
│ Group 2 (2 videos) - 92% similar                           │
│ ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Full Analysis (Week 1)
- [ ] Add sentiment analysis to transcription pipeline
- [ ] Create batch analysis endpoint
- [ ] Add progress tracking
- [ ] Create analysis coverage dashboard widget

### Phase 2: Duplicate Detection (Week 2)
- [ ] Implement transcript similarity matching
- [ ] Create duplicate grouping logic
- [ ] Build duplicate manager UI
- [ ] Implement file deletion with safety checks
- [ ] Add deletion audit logging

### Phase 3: Auto-Curation (Week 3)
- [ ] Implement sentiment-based auto-curation rules
- [ ] Create settings UI for thresholds
- [ ] Add auto-curation preview endpoint
- [ ] Build auto-curation stats widget

### Phase 4: Bulk Tools (Week 4)
- [ ] Implement bulk approve/deny endpoints
- [ ] Add filter-based bulk operations
- [ ] Create bulk actions toolbar in UI
- [ ] Add keyboard shortcuts
- [ ] Implement undo functionality

### Phase 5: Integration (Week 5)
- [ ] Update narrative builder queries
- [ ] Add curation status filters
- [ ] Create approved content stats
- [ ] End-to-end testing

---

## Technical Architecture

### New Database Columns

```sql
-- Media table additions
ALTER TABLE media ADD COLUMN sentiment_score DECIMAL(4,3);
ALTER TABLE media ADD COLUMN sentiment_label VARCHAR(20);
ALTER TABLE media ADD COLUMN transcript_hash VARCHAR(64);
ALTER TABLE media ADD COLUMN auto_curated BOOLEAN DEFAULT FALSE;
ALTER TABLE media ADD COLUMN auto_curation_reason TEXT;

-- Deletion audit log
CREATE TABLE deletion_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  media_id UUID,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT,
  deleted_at TIMESTAMP DEFAULT NOW(),
  deleted_by TEXT DEFAULT 'system',
  reason TEXT,
  duplicate_group_id UUID
);
```

### New Services

1. **SentimentAnalyzer** - Analyzes transcript sentiment using OpenAI
2. **DuplicateDetector** - Finds similar transcripts using fuzzy matching
3. **AutoCurator** - Applies rules to auto-approve/deny content
4. **BulkCurator** - Handles bulk curation operations

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Accidental file deletion | Require confirmation, audit log, show file count |
| Wrong auto-curation | Preview mode, manual override, adjustable thresholds |
| Analysis costs | Batch processing, skip already-analyzed files |
| Sentiment misclassification | Conservative thresholds, human review for edge cases |

---

## Dependencies

- **OpenAI API**: Sentiment analysis
- **rapidfuzz**: Transcript similarity matching
- **PostgreSQL**: Database storage

---

## Acceptance Criteria

1. ✅ All videos have complete analysis (transcript + sentiment)
2. ✅ Duplicate videos can be identified and bulk deleted
3. ✅ Auto-curation reduces manual review load by 40%+
4. ✅ Bulk tools enable 5x faster human curation
5. ✅ Narrative builder only uses approved content
6. ✅ No accidental data loss (audit trail exists)

---

*Document Version: 1.0*
*Created: December 25, 2024*
*Author: AI-Assisted Development*
