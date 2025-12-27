# Media Factory Implementation Phases

**Version:** 1.0  
**Date:** December 26, 2024  
**Status:** Planning

---

## Phase 1: Foundation (Week 1-2)

### 1.1 SAM 2 Matting Service ✅ Priority

**Goal**: Implement video matting using SAM 2 via Hugging Face API

**Tasks**:
- [ ] Research SAM 2 Hugging Face API availability
- [ ] Test SAM 2 via Hugging Face Inference API or Spaces API
- [ ] Create matting service structure
- [ ] Implement SAM 2 adapter (Hugging Face API)
- [ ] Create matting worker
- [ ] Create API endpoints
- [ ] Integration tests

**Deliverables**:
- `Backend/services/matting/worker.py`
- `Backend/services/matting/models/sam2.py` (Hugging Face API)
- `Backend/api/endpoints/matting.py`
- Test script: `Backend/scripts/test_sam2_huggingface.py`

**Success Criteria**:
- Can segment objects/people from video via Hugging Face API
- Works on Mac and Windows (API-based, not local)
- Processes video frames and outputs alpha channel

**Fallback**: If SAM 2 API not available, use RMBG-1.4 (rembg) as primary, SAM 2 as future enhancement

---

### 1.2 Remotion Service - Basic Composition

**Goal**: Implement Remotion service with basic composition support

**Tasks**:
- [ ] Create Remotion service structure
- [ ] Implement timeline.json parser
- [ ] Create Remotion composition builder
- [ ] Implement basic rendering (single source)
- [ ] Create Remotion worker
- [ ] Create API endpoints
- [ ] Integration with TTS service (subscribe to `tts.completed`)

**Deliverables**:
- `Backend/services/remotion/worker.py`
- `Backend/services/remotion/composer.py`
- `Backend/services/remotion/models.py`
- `Backend/api/endpoints/remotion.py`

**Success Criteria**:
- Can render video from timeline.json
- Supports voice + music audio layers
- Supports basic text overlays
- Outputs MP4 file

---

### 1.3 Content Brief Enhancement

**Goal**: Enhance existing content brief system with scoring and templates

**Tasks**:
- [ ] Add "Worth Covering" scoring (0-100)
- [ ] Implement trend clustering
- [ ] Add angle generation (niche convergence)
- [ ] Create brief template system
- [ ] Add brief → script.json conversion
- [ ] Integration with trend analysis

**Deliverables**:
- Enhanced `Backend/services/trend_brief_service.py`
- Brief scoring module
- Brief template system
- Script generator service

**Success Criteria**:
- Can generate scored briefs from trends
- Briefs include script beats and visual plan
- Briefs can trigger pipeline automatically

---

## Phase 2: Integration (Week 3-4)

### 2.1 End-to-End Pipeline

**Goal**: Connect all stages (Brief → Script → TTS → Remotion → Publish)

**Tasks**:
- [ ] Create pipeline orchestrator
- [ ] Implement stage-to-stage event flow
- [ ] Add pipeline status tracking
- [ ] Error handling and retry logic
- [ ] Progress tracking across stages
- [ ] Integration tests

**Deliverables**:
- `Backend/services/pipeline/orchestrator.py`
- Pipeline status tracking
- End-to-end test suite

**Success Criteria**:
- Can process brief → published video
- All stages communicate via events
- Progress visible at each stage
- Errors handled gracefully

---

### 2.2 Remotion Multi-Source Support

**Goal**: Support multiple source types in Remotion

**Tasks**:
- [ ] Implement source loader (local, URL, TTS, MediaPoster)
- [ ] Add source caching
- [ ] Support UGC matting integration
- [ ] Support b-roll selection
- [ ] Support meme templates

**Deliverables**:
- `Backend/services/remotion/source_loader.py`
- Source caching system
- Integration with matting service

**Success Criteria**:
- Can load sources from multiple types
- Sources cached for performance
- Matting outputs integrated seamlessly

---

### 2.3 Quality Gates

**Goal**: Implement quality validation at each stage

**Tasks**:
- [ ] Audio quality checks (TTS output)
- [ ] Video quality checks (Remotion output)
- [ ] Caption accuracy validation
- [ ] Pacing validation (hook timing, pattern interrupts)
- [ ] Acceptance checklist automation

**Deliverables**:
- Quality validation modules
- Acceptance checklist automation
- Quality reports

**Success Criteria**:
- Quality gates prevent low-quality output
- Automated acceptance checks
- Quality reports generated

---

## Phase 3: Enhancement (Week 5-6)

### 3.1 Music Service

**Goal**: Implement music bed generation/selection

**Tasks**:
- [ ] Research Suno API / SoundCloud API
- [ ] Create music service structure
- [ ] Implement music selection/generation
- [ ] Add music ducking rules
- [ ] Create music worker
- [ ] Create API endpoints

**Deliverables**:
- `Backend/services/music/worker.py`
- Music service adapters
- `Backend/api/endpoints/music.py`

**Success Criteria**:
- Can generate/select music based on mood/BPM
- Music properly ducked under voice
- Music duration matches video

---

### 3.2 B-Roll Generation/Selection

**Goal**: Automatically select or generate b-roll

**Tasks**:
- [ ] Integrate with stock footage APIs
- [ ] Implement keyword-based selection
- [ ] Add b-roll caching
- [ ] Support AI-generated visuals (icons, diagrams)
- [ ] Integration with Remotion

**Deliverables**:
- B-roll selection service
- Stock footage integration
- AI visual generation (future)

**Success Criteria**:
- Can select b-roll based on keywords
- B-roll cached for reuse
- B-roll integrated into Remotion timeline

---

### 3.3 Meme Template System

**Goal**: Support meme templates in videos

**Tasks**:
- [ ] Create meme template library
- [ ] Implement meme text overlay
- [ ] Add meme animation system
- [ ] Integration with Remotion

**Deliverables**:
- Meme template system
- Meme animation library
- Remotion meme components

**Success Criteria**:
- Can apply meme templates to videos
- Memes animated and timed correctly
- Memes integrated into Remotion timeline

---

### 3.4 Multi-Variant Rendering

**Goal**: Generate multiple platform variants (Shorts, Reels, TikTok)

**Tasks**:
- [ ] Implement format-specific compositions
- [ ] Add aspect ratio handling
- [ ] Support platform-specific optimizations
- [ ] Batch rendering

**Deliverables**:
- Multi-variant renderer
- Format-specific templates
- Batch rendering system

**Success Criteria**:
- Can render multiple variants from one brief
- Variants optimized for each platform
- Batch rendering efficient

---

## Phase 4: Optimization (Week 7-8)

### 4.1 Performance Optimization

**Tasks**:
- [ ] Optimize rendering times
- [ ] Implement caching strategies
- [ ] Parallel processing where possible
- [ ] Resource usage optimization

**Success Criteria**:
- Render time <5 minutes for 45s video
- Efficient resource usage
- Scalable to multiple concurrent jobs

---

### 4.2 Error Recovery & Retry Logic

**Tasks**:
- [ ] Implement retry logic for each stage
- [ ] Add dead-letter queue handling
- [ ] Partial failure recovery
- [ ] Error reporting and alerts

**Success Criteria**:
- Failed jobs automatically retried
- Partial failures handled gracefully
- Error reporting comprehensive

---

### 4.3 Comprehensive Testing

**Tasks**:
- [ ] Unit tests for all services
- [ ] Integration tests for pipeline
- [ ] End-to-end tests
- [ ] Performance tests
- [ ] Load tests

**Success Criteria**:
- >90% test coverage
- All critical paths tested
- Performance benchmarks met

---

### 4.4 Documentation & Deployment

**Tasks**:
- [ ] API documentation
- [ ] Deployment guides
- [ ] Troubleshooting guides
- [ ] User guides
- [ ] Architecture diagrams

**Success Criteria**:
- Complete documentation
- Deployment guides for all environments
- Troubleshooting resources available

---

## Success Metrics

### Phase 1
- ✅ TTS Service working
- ✅ SAM 2 Matting Service working (via API)
- ✅ Remotion Service basic composition working
- ✅ Content Brief scoring working

### Phase 2
- ✅ End-to-end pipeline working
- ✅ Multi-source support in Remotion
- ✅ Quality gates implemented

### Phase 3
- ✅ Music Service working
- ✅ B-roll selection working
- ✅ Meme templates working
- ✅ Multi-variant rendering working

### Phase 4
- ✅ Performance optimized
- ✅ Error recovery working
- ✅ Comprehensive tests passing
- ✅ Documentation complete

---

## Dependencies

### External Services
- Hugging Face API (TTS, SAM 2)
- Suno API / SoundCloud API (Music)
- Stock footage APIs (B-roll)
- Remotion (Local, but containerizable)

### Internal Services
- MediaPoster Event Bus
- MediaPoster Publishing Service
- MediaPoster Trend Analysis
- MediaPoster Media Library

---

## Risk Mitigation

### Risk 1: SAM 2 API Not Available
**Mitigation**: Use RMBG-1.4 as primary, SAM 2 as future enhancement

### Risk 2: Remotion Performance
**Mitigation**: Implement caching, optimize compositions, consider pre-rendering

### Risk 3: Quality Issues
**Mitigation**: Implement quality gates, automated testing, manual review option

### Risk 4: Cross-Platform Compatibility
**Mitigation**: Use APIs (not local models), containerize services, test on all platforms

---

## Next Steps

1. **Immediate**: Test SAM 2 via Hugging Face API
2. **Week 1**: Implement SAM 2 Matting Service
3. **Week 1-2**: Implement Remotion Service (basic)
4. **Week 2**: Enhance Content Brief System
5. **Week 3-4**: Integration and testing
6. **Week 5-6**: Enhancements
7. **Week 7-8**: Optimization and documentation

