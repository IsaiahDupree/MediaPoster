# Video Style Template Analysis

**Date:** January 2025  
**Videos Analyzed:** 7 YouTube videos  
**Purpose:** Extract reusable style templates to recreate videos in the same style with new content

---

## 📊 Analysis Summary

### Videos Analyzed

1. **The Impossible to Debunk UFO Events** (620s)
2. **Every Interrogation Technique Explained in 8 Minutes** (462s)
3. **Every Sim Racing Driver Explained in 9 Minutes** (587s)
4. **The Jailbreaks You NEED For 2026** (976s)
5. **getting jacked is easy, actually** (653s)
6. **Every Hidden Advantage of Your Birth Month Explained** (1042s)
7. **History's Biggest Cover-Ups Explained in 20 Minutes** (1253s)

---

## 🎯 Key Patterns Discovered

### Hook Archetypes (Most Common → Least Common)

1. **Curiosity-driven** (2 videos) - "Have you ever seen a UFO?", "What if I told you..."
2. **Every X Explained** (1 video) - "Every Interrogation Technique Explained..."
3. **Every type of X explained** (1 video) - "Every Sim Racing Driver Explained..."
4. **You NEED to know X** (1 video) - "The Jailbreaks You NEED For 2026"
5. **It's easier than you think** (1 video) - "getting jacked is easy, actually"
6. **Nobody tells you** (1 video) - Variations of hidden information

### Content Styles

- **Explainer** (5 videos) - Most common style
- **Listicle** (1 video) - List-based content
- **Listicle with narrative** (1 video) - List with storytelling elements

### Pacing

- **Medium pacing** (7/7 videos) - Consistent across all videos
- **Medium cut density** - Not too fast, not too slow

### Visual Style

- **Mixed shots** (4 videos) - Combination of talking head, b-roll, graphics
- **Talking head** (3 videos) - Direct-to-camera presentation
- **Text overlays** - Static captions at bottom (most common)

### CTA Patterns

- **Engagement CTAs** (7/7 videos) - All videos use engagement-focused CTAs
- **Placement:** Closing (7/7 videos) - CTAs consistently at the end

### Emotional Triggers

- **Curiosity** - Primary emotion across most videos
- **Mystery of the unknown** - Common trigger
- **Relatable information** - "Nobody tells you" patterns

---

## 📋 Template Structure

Each template includes:

1. **Structure Pattern**
   - Hook duration (typically 3-5 seconds)
   - Body structure (listicle, explainer, narrative)
   - CTA placement (closing)

2. **Beat Sheet Template**
   - Timestamped beats with roles (hook, problem, solution, proof, cta)
   - Summary of each beat's purpose

3. **Style Elements**
   - Hook archetype and examples
   - Pacing and cut density
   - Visual style (shot types, text overlays, color scheme)

4. **Content Style**
   - Content type (tutorial, explainer, listicle, etc.)
   - Tone (casual, professional, energetic)
   - Complexity level (simple, medium, technical)

5. **Replication Guide**
   - Step-by-step instructions
   - Key patterns that make the style work

---

## 🎬 How to Use These Templates

### Step 1: Choose a Template

Review the templates in `Backend/data/video_style_templates/`:
- `template_Om0d0u1ASJY.json` - Curiosity-driven listicle
- `template_DScr9hwfcas.json` - "Every X Explained" format
- `template_HSmHYWBy0ss.json` - "Every type of X" format
- `template_oBYM1bEpGB0.json` - "You NEED to know X" format
- `template_XOtMZchugyQ.json` - "It's easier than you think" format
- `template_Dgzb6ojbjWg.json` - "Every Hidden X" format
- `template_v4LDsaWNjaM.json` - Historical explainer format

### Step 2: Extract the Style Elements

From your chosen template, extract:
- **Hook archetype** - Use the same pattern with your topic
- **Beat sheet** - Follow the same structure and timing
- **Visual style** - Match shot types and text overlay style
- **Pacing** - Maintain the same rhythm

### Step 3: Apply to New Content

1. **Hook**: Use the hook archetype with your topic
   - Example: "Every [Your Topic] Explained in [X] Minutes"
   - Example: "The [Your Topic] You NEED to Know"

2. **Structure**: Follow the beat sheet template
   - Hook (0-5 seconds)
   - Body (organized by the template's structure)
   - CTA (closing)

3. **Visuals**: Match the visual style
   - Shot types (talking head, mixed, b-roll)
   - Text overlay style (static captions, animated, etc.)
   - Color scheme (if specified)

4. **Pacing**: Maintain medium pacing with medium cut density

### Step 4: Generate Content

Use the template's replication guide to:
- Write script following the beat sheet
- Create visuals matching the style
- Edit with the specified pacing and cut density
- Add CTAs matching the template's pattern

---

## 🔧 Technical Implementation

### Files Created

- **Individual Templates**: `Backend/data/video_style_templates/template_*.json`
- **Aggregated Analysis**: `Backend/data/video_style_templates/aggregated_templates.json`
- **Script**: `Backend/scripts/analyze_video_style_templates.py`

### Template Schema

```python
@dataclass
class VideoStyleTemplate:
    template_id: str
    source_video_url: str
    source_video_title: str
    structure_pattern: Dict[str, Any]
    beat_sheet_template: List[Dict[str, Any]]
    hook_archetype: str
    hook_examples: List[str]
    pacing: str
    cut_density: str
    primary_shot_type: str
    text_overlay_style: Dict[str, Any]
    content_style: str
    tone: str
    complexity: str
    cta_type: str
    cta_placement: str
    primary_emotion: str
    replication_guide: str
    # ... optional fields
```

---

## 🚀 Next Steps

### 1. Create Video Generation Script

Use these templates to generate new videos:
- Load a template
- Generate script following the beat sheet
- Create visuals matching the style
- Render video with specified pacing

### 2. Template-Based Content Generator

Build a system that:
- Takes a topic and template ID
- Generates script following the template's structure
- Creates video using the template's visual style
- Outputs a video matching the analyzed style

### 3. Style Mixing

Combine elements from multiple templates:
- Use hook from Template A
- Use structure from Template B
- Use visual style from Template C

### 4. Automated Style Matching

Analyze your own videos and match them to these templates:
- Identify which template your video follows
- Suggest improvements based on successful patterns
- Generate variations using different templates

---

## 📈 Success Metrics

After using these templates, track:
- **Engagement rates** - Compare to original videos
- **View duration** - Match pacing effectiveness
- **Hook effectiveness** - Test different hook archetypes
- **CTA conversion** - Measure engagement CTA performance

---

## 📚 References

- **Templates**: `Backend/data/video_style_templates/`
- **Analysis Script**: `Backend/scripts/analyze_video_style_templates.py`
- **Aggregated Data**: `Backend/data/video_style_templates/aggregated_templates.json`

---

*Last Updated: January 2025*

