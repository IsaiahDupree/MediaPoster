# AI Mock Calls Audit

**Date:** December 24, 2025  
**Purpose:** Identify all places using mock AI calls instead of real OpenAI/AI API calls

---

## 🔴 Critical: Mock AI in Production Code

### 1. **Backend/services/ai_content_generator.py**
**Status:** ❌ TODO - Not Implemented  
**Issue:** All AI generation methods have TODO comments and return mock data

**Mock Implementations:**
- `_generate_with_openai()` - Line 178: `# TODO: Implement OpenAI API calls`
- `_generate_with_anthropic()` - Line 192: `# TODO: Implement Anthropic API calls`
- `_generate_image_stability()` - Line 201: `# TODO: Implement Stability AI API calls`
- `_generate_image_dalle()` - Line 206: `# TODO: Implement DALL-E API calls`
- `_generate_video_runway()` - Line 211: `# TODO: Implement Runway ML API calls`

**Impact:** 
- Blog post generation returns mock data
- Image generation returns fake URLs
- Video generation returns fake URLs
- Carousel generation uses mock images

**Recommendation:** Implement real API calls for all providers

---

### 2. **Backend/api/comment_automation.py**
**Status:** ❌ Mock AI  
**Issue:** Comment summarization uses mock logic

**Location:** Line 432-438
```python
def _summarize_comments(comments: List[Dict]) -> str:
    """Generate summary of top comments (mock AI)"""
    # Mock summary - in production would use AI
    themes = ["enthusiasm", "appreciation", "questions", "support"]
    return f"Top comments show {random.choice(themes)}..."
```

**Impact:** Comment summaries are generic, not AI-generated insights

**Recommendation:** Use OpenAI to analyze comment sentiment, themes, and generate real summaries

---

### 3. **Backend/api/endpoints/publishing_analytics.py**
**Status:** ❌ TODO - Not Implemented  
**Issue:** Content variant generation uses hardcoded examples

**Location:** Line 89
```python
# TODO: Call AI service (OpenAI GPT) to generate
```

**Impact:** Title/caption variants are static templates, not AI-generated

**Recommendation:** Use OpenAI to generate creative variants based on original content

---

### 4. **Backend/services/brief_generator.py**
**Status:** ❌ Mock AI Logic  
**Issue:** Content brief generation uses simple templates

**Location:** Line 30
```python
# Mock AI Logic
# In production, this would use an LLM with the insights as context
```

**Impact:** Content briefs are template-based, not AI-analyzed

**Recommendation:** Use OpenAI/Anthropic to analyze segment insights and generate strategic briefs

---

### 5. **Backend/services/content_brief.py**
**Status:** ❌ TODO - Not Implemented  
**Issue:** Hook template generation uses simple templates

**Location:** Line 259
```python
"""Generate hook templates (TODO: Use AI)"""
```

**Impact:** Hooks are generic templates, not AI-optimized

**Recommendation:** Use AI to generate hooks based on content analysis

---

### 6. **Backend/api/image_analysis.py**
**Status:** ⚠️ Has Mock Fallback  
**Issue:** `analyze_with_mock()` function exists and may be used when OpenAI fails

**Location:** Line 494-589
```python
async def analyze_with_mock(custom_fields: List[str]) -> Dict[str, Any]:
    """Generate mock analysis for testing"""
```

**Impact:** If OpenAI fails, falls back to mock data instead of error handling

**Recommendation:** Ensure proper error handling and only use mock in test environments

---

### 7. **Backend/services/intelligence/content_brief.py**
**Status:** ⚠️ Has Mock Fallback  
**Issue:** Falls back to mock when OpenAI client not available

**Location:** Line 33-34
```python
if not self.client:
    return self._mock_brief(segment_name)
```

**Impact:** If OpenAI key missing, returns mock briefs instead of error

**Recommendation:** Add proper error handling and configuration validation

---

## 🟡 Conditional: Mock Only When API Key Missing

### 8. **Backend/services/clip_extraction_service.py**
**Status:** ⚠️ Mock Fallback for Transcription  
**Issue:** Uses mock transcription when AssemblyAI not installed

**Location:** Line 298-312
```python
async def _mock_transcribe(self, video_path: Path) -> Dict[str, Any]:
    """Mock transcription for testing without AssemblyAI."""
```

**Impact:** Falls back to mock transcript if AssemblyAI unavailable

**Recommendation:** This is acceptable as a fallback, but should log warning

---

## ✅ Acceptable: Test/Development Only

### 9. **Backend/services/ai_providers/mock_provider.py**
**Status:** ✅ Test Only  
**Issue:** None - This is intentionally for testing

**Purpose:** Provides deterministic mock results for unit tests

**Recommendation:** Keep as-is, only used when `AI_PROVIDER=mock`

---

## 📊 Summary

### By Priority

**🔴 High Priority (Production Code):**
1. `ai_content_generator.py` - All generation methods
2. `comment_automation.py` - Comment summarization
3. `publishing_analytics.py` - Content variant generation
4. `brief_generator.py` - Content brief generation
5. `content_brief.py` - Hook template generation

**🟡 Medium Priority (Fallbacks):**
6. `intelligence/content_brief.py` - Mock fallback when key missing
7. `image_analysis.py` - Mock fallback function

**✅ Low Priority (Test/Dev):**
8. `clip_extraction_service.py` - Mock transcription fallback (acceptable)
9. `ai_providers/mock_provider.py` - Test provider (intentional)

---

## 🔧 Implementation Recommendations

### 1. **AI Content Generator** (`ai_content_generator.py`)
**Action:** Implement real OpenAI/Anthropic API calls

```python
async def _generate_with_openai(self, prompt: str, content_type: str) -> Dict[str, Any]:
    """Generate content using OpenAI"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=self.openai_key)
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are an expert {content_type} writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return {
        "title": extract_title(response.choices[0].message.content),
        "body": response.choices[0].message.content,
        "provider": "openai"
    }
```

### 2. **Comment Summarization** (`comment_automation.py`)
**Action:** Use OpenAI to analyze comments

```python
async def _summarize_comments(comments: List[Dict]) -> str:
    """Generate AI summary of top comments"""
    from openai import AsyncOpenAI
    import os
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    comment_texts = [c.get('text', '') for c in comments[:20]]
    prompt = f"Analyze these comments and provide insights:\n\n" + "\n".join(comment_texts)
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert at analyzing social media engagement."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content
```

### 3. **Content Variants** (`publishing_analytics.py`)
**Action:** Use OpenAI to generate variants

```python
async def generate_variants(request: VariantRequest) -> Dict:
    """Generate AI variants using OpenAI"""
    from openai import AsyncOpenAI
    import os
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"Generate 5 creative {request.type} variants for: {request.original_text}"
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a creative social media copywriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )
    
    # Parse variants from response
    variants = parse_variants(response.choices[0].message.content)
    return {"variants": variants}
```

### 4. **Content Briefs** (`brief_generator.py`)
**Action:** Use OpenAI to analyze insights and generate briefs

```python
async def generate_briefs_for_segment(
    segment_id: UUID, 
    insights: SegmentInsightResponse
) -> List[ContentBrief]:
    """Generate AI-powered content briefs"""
    from openai import AsyncOpenAI
    import os
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    Analyze this segment's insights and generate 3 content briefs:
    - Top topics: {insights.top_topics}
    - Best platforms: {insights.top_platforms}
    - Engagement patterns: {insights.engagement_patterns}
    
    Generate strategic content briefs with hooks, angles, and talking points.
    """
    
    response = await client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a content strategist expert."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    # Parse JSON response into ContentBrief objects
    return parse_briefs_from_json(response.choices[0].message.content)
```

### 5. **Hook Templates** (`content_brief.py`)
**Action:** Use AI to generate hooks

```python
def _generate_hook_templates(
    self,
    insights: SegmentInsight,
    goal: str,
    top_content: List[ContentItem]
) -> List[str]:
    """Generate AI-powered hook templates"""
    from openai import AsyncOpenAI
    import os
    
    if not os.getenv("OPENAI_API_KEY"):
        # Fallback to templates if no key
        return self._template_hooks(insights)
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    Generate 10 viral hook templates for:
    - Topics: {insights.top_topics}
    - Goal: {goal}
    - Top performing content: {[c.title for c in top_content[:3]]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a viral content hook expert."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return parse_hooks_from_response(response.choices[0].message.content)
```

---

## 🎯 Action Items

1. **Immediate (High Priority):**
   - [ ] Implement OpenAI calls in `ai_content_generator.py`
   - [ ] Replace mock comment summarization with real AI
   - [ ] Implement variant generation with OpenAI
   - [ ] Replace mock brief generation with AI

2. **Short-term (Medium Priority):**
   - [ ] Add proper error handling for missing API keys
   - [ ] Ensure mock fallbacks only in test/dev environments
   - [ ] Add logging when falling back to mocks

3. **Long-term:**
   - [ ] Add configuration to disable mock fallbacks in production
   - [ ] Create health checks for AI service availability
   - [ ] Add metrics for AI call success/failure rates

---

## 📝 Notes

- Mock providers are acceptable for **testing only**
- Production code should **never** use mocks unless explicitly configured
- All AI services should have proper error handling
- Missing API keys should result in clear errors, not silent mock fallbacks
- Consider adding feature flags to enable/disable AI features

---

---

## 🔍 Configuration Check

### Environment Variables

The system uses `AI_PROVIDER` environment variable to determine which provider to use:
- `AI_PROVIDER=openai` (default) - Uses real OpenAI
- `AI_PROVIDER=mock` - Uses mock provider (testing only)
- `AI_PROVIDER=anthropic` - Uses Anthropic (if implemented)

**Current Default:** `openai` ✅ (Good - defaults to real AI)

### Services Using Provider System

✅ **Correctly Using Provider System:**
- `services/clip_extraction_service.py` - Uses `get_ai_provider()`
- `services/ai_providers/__init__.py` - Factory function defaults to OpenAI

❌ **NOT Using Provider System (Hardcoded Mocks):**
- `services/ai_content_generator.py` - Has TODO comments, returns mocks
- `api/comment_automation.py` - Hardcoded mock logic
- `api/endpoints/publishing_analytics.py` - Hardcoded mock variants
- `services/brief_generator.py` - Hardcoded mock logic
- `services/content_brief.py` - Hardcoded templates

### Quick Check Script

Run this to find all mock AI usage:

```bash
# Find TODO comments for AI
grep -r "TODO.*[Aa][Ii]" Backend/ --include="*.py"

# Find mock AI functions
grep -r "mock.*ai\|mock.*openai" Backend/ --include="*.py" -i

# Find hardcoded mock returns
grep -r "Mock.*summary\|mock.*content\|mock.*generation" Backend/ --include="*.py" -i
```

---

**Last Updated:** December 24, 2025

