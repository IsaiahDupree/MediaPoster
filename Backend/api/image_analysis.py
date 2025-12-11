"""
AI Image Analysis API
Comprehensive image analysis using AI vision models.
Extracts: people, clothing, emotions, scene, location, time, objects, and more.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid
import base64
import httpx
import os
import json

router = APIRouter(prefix="/api/image-analysis", tags=["Image Analysis"])


# ============================================================================
# MODELS
# ============================================================================

class EmotionType(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"
    CONFIDENT = "confident"
    RELAXED = "relaxed"
    FOCUSED = "focused"


class TimeOfDay(str, Enum):
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    SUNSET = "sunset"
    NIGHT = "night"
    UNKNOWN = "unknown"


class SceneType(str, Enum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    URBAN = "urban"
    NATURE = "nature"
    BEACH = "beach"
    MOUNTAIN = "mountain"
    STUDIO = "studio"
    HOME = "home"
    OFFICE = "office"
    RESTAURANT = "restaurant"
    EVENT = "event"
    STREET = "street"
    OTHER = "other"


class PersonAnalysis(BaseModel):
    """Analysis of a person in the image"""
    person_id: int = Field(description="Index of person in image")
    position: str = Field(description="Position in frame: left, center, right, foreground, background")
    
    # Physical appearance
    approximate_age: str = Field(description="Estimated age range")
    gender_presentation: str = Field(description="Perceived gender presentation")
    ethnicity_note: Optional[str] = Field(default=None, description="Cultural/ethnic appearance notes if relevant")
    
    # Clothing
    clothing_description: str = Field(description="Detailed clothing description")
    clothing_style: str = Field(description="Style category: casual, formal, athletic, etc.")
    clothing_colors: List[str] = Field(description="Main colors in clothing")
    accessories: List[str] = Field(default=[], description="Visible accessories")
    
    # Expression & Emotion
    facial_expression: str = Field(description="Description of facial expression")
    primary_emotion: EmotionType = Field(description="Primary emotion detected")
    secondary_emotion: Optional[EmotionType] = Field(default=None)
    emotion_confidence: float = Field(description="Confidence in emotion detection 0-1")
    
    # Pose & Action
    body_pose: str = Field(description="Description of body pose")
    apparent_action: str = Field(description="What the person appears to be doing")
    gaze_direction: str = Field(description="Where the person is looking")
    
    # Additional notes
    notable_features: List[str] = Field(default=[], description="Notable features")


class ObjectDetection(BaseModel):
    """Detected object in the image"""
    name: str
    category: str
    position: str
    prominence: str  # foreground, midground, background
    color: Optional[str] = None
    description: Optional[str] = None


class ImageAnalysisResult(BaseModel):
    """Complete image analysis result"""
    analysis_id: str = Field(description="Unique ID for this analysis")
    image_url: Optional[str] = Field(default=None)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Overall description
    title: str = Field(description="Short title for the image (5-10 words)")
    short_description: str = Field(description="Brief description (1-2 sentences)")
    detailed_description: str = Field(description="Comprehensive description (100-500 words)")
    
    # Scene Analysis
    scene_type: SceneType
    scene_setting: str = Field(description="Specific setting description")
    indoor_outdoor: str = Field(description="indoor, outdoor, or mixed")
    
    # Location & Environment
    location_type: str = Field(description="Type of location")
    location_guess: Optional[str] = Field(default=None, description="Guessed specific location if identifiable")
    environment_description: str = Field(description="Description of environment/surroundings")
    weather_conditions: Optional[str] = Field(default=None, description="Weather if visible")
    
    # Time Analysis
    time_of_day: TimeOfDay
    time_indicators: List[str] = Field(description="What indicates the time of day")
    season_guess: Optional[str] = Field(default=None, description="Estimated season if detectable")
    
    # People Analysis
    people_count: int = Field(description="Number of people visible")
    people: List[PersonAnalysis] = Field(default=[], description="Detailed analysis of each person")
    group_dynamics: Optional[str] = Field(default=None, description="Interaction between people")
    
    # Objects & Elements
    main_subjects: List[str] = Field(description="Main subjects of the image")
    objects_detected: List[ObjectDetection] = Field(default=[])
    background_elements: List[str] = Field(default=[])
    foreground_elements: List[str] = Field(default=[])
    
    # Colors & Aesthetics
    dominant_colors: List[str] = Field(description="Main colors in the image")
    color_palette: str = Field(description="Description of color scheme")
    lighting_type: str = Field(description="Type of lighting")
    lighting_quality: str = Field(description="Quality/mood of lighting")
    contrast_level: str = Field(description="Low, medium, high contrast")
    
    # Composition
    composition_style: str = Field(description="Composition technique used")
    focal_point: str = Field(description="Main focal point of image")
    depth_of_field: str = Field(description="Shallow, medium, deep")
    perspective: str = Field(description="Camera perspective/angle")
    
    # Mood & Style
    overall_mood: str = Field(description="Overall mood/atmosphere")
    visual_style: str = Field(description="Visual/artistic style")
    aesthetic_tags: List[str] = Field(default=[], description="Aesthetic descriptors")
    
    # Content Classification
    content_type: str = Field(description="Type of content: portrait, landscape, product, etc.")
    content_category: str = Field(description="Category for social media")
    suitable_platforms: List[str] = Field(description="Best platforms for this image")
    
    # Text & Branding
    visible_text: List[str] = Field(default=[], description="Any visible text in image")
    brand_logos: List[str] = Field(default=[], description="Visible brand logos")
    
    # Social Media Optimization
    suggested_hashtags: List[str] = Field(default=[])
    suggested_caption: str = Field(description="AI-generated caption suggestion")
    engagement_prediction: str = Field(description="Predicted engagement level")
    
    # Technical Quality
    image_quality: str = Field(description="Overall quality assessment")
    sharpness: str = Field(description="Sharpness level")
    exposure: str = Field(description="Exposure assessment")
    
    # Custom Fields
    custom_fields: Dict[str, Any] = Field(default={}, description="User-defined custom analysis fields")
    
    # Raw AI response
    raw_analysis: Optional[str] = Field(default=None, description="Raw AI analysis text")
    
    # Confidence & Meta
    overall_confidence: float = Field(description="Overall confidence 0-1")
    processing_time_ms: int = Field(description="Processing time in milliseconds")


class AnalysisRequest(BaseModel):
    """Request for image analysis"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    custom_fields: List[str] = Field(default=[], description="Additional fields to analyze")
    analysis_depth: str = Field(default="detailed", description="brief, standard, detailed, comprehensive")
    focus_areas: List[str] = Field(default=[], description="Specific areas to focus on")


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

analyses_store: Dict[str, ImageAnalysisResult] = {}


# ============================================================================
# AI ANALYSIS FUNCTIONS
# ============================================================================

def get_analysis_prompt(custom_fields: List[str], focus_areas: List[str], depth: str) -> str:
    """Generate the analysis prompt for the AI"""
    
    base_prompt = """Analyze this image in comprehensive detail. Provide a thorough analysis covering ALL of the following aspects. Be specific and detailed.

## REQUIRED ANALYSIS SECTIONS:

### 1. OVERALL DESCRIPTION
- **Title**: A catchy 5-10 word title
- **Short Description**: 1-2 sentence summary
- **Detailed Description**: 100-500 word comprehensive description of everything in the image

### 2. SCENE ANALYSIS
- **Scene Type**: indoor/outdoor/urban/nature/studio/etc.
- **Setting**: Specific setting description
- **Environment**: Surroundings and atmosphere

### 3. LOCATION & TIME
- **Location Type**: Where this appears to be
- **Time of Day**: dawn/morning/midday/afternoon/evening/sunset/night
- **Time Indicators**: What tells us the time
- **Weather**: If visible
- **Season**: If detectable

### 4. PEOPLE ANALYSIS (for each person visible)
- **Position**: Where in the frame
- **Age Range**: Approximate
- **Clothing**: Detailed description, style, colors
- **Accessories**: Items worn or carried
- **Facial Expression**: Description
- **Primary Emotion**: happy/sad/angry/surprised/neutral/excited/thoughtful/confident/relaxed/focused
- **Body Pose**: Description
- **Action**: What they appear to be doing
- **Gaze Direction**: Where looking
- **Notable Features**: Anything distinctive

### 5. OBJECTS & ELEMENTS
- **Main Subjects**: What is the image about
- **Objects**: List all visible objects with positions
- **Background**: What's in the background
- **Foreground**: What's in the foreground

### 6. COLORS & AESTHETICS
- **Dominant Colors**: Main colors (list 3-5)
- **Color Palette**: Warm/cool/neutral/vibrant/muted
- **Lighting Type**: Natural/artificial/mixed/studio
- **Lighting Quality**: Soft/harsh/dramatic/flat
- **Contrast**: Low/medium/high

### 7. COMPOSITION & TECHNICAL
- **Composition Style**: Rule of thirds/centered/diagonal/etc.
- **Focal Point**: Main focus
- **Depth of Field**: Shallow/medium/deep
- **Perspective**: Eye level/low angle/high angle/etc.
- **Image Quality**: Overall quality
- **Sharpness**: Assessment
- **Exposure**: Under/correct/over

### 8. MOOD & STYLE
- **Overall Mood**: Atmosphere/feeling
- **Visual Style**: Artistic style
- **Aesthetic Tags**: 5-10 descriptive tags

### 9. CONTENT CLASSIFICATION
- **Content Type**: Portrait/landscape/product/lifestyle/etc.
- **Category**: Social media category
- **Suitable Platforms**: Best platforms for posting

### 10. TEXT & BRANDING
- **Visible Text**: Any readable text
- **Brand Logos**: Any visible brands

### 11. SOCIAL MEDIA OPTIMIZATION
- **Hashtags**: 10-15 relevant hashtags
- **Caption Suggestion**: Engaging caption for social media
- **Engagement Prediction**: Low/medium/high expected engagement"""

    if custom_fields:
        base_prompt += "\n\n### 12. CUSTOM FIELDS\n"
        for field in custom_fields:
            base_prompt += f"- **{field}**: Analyze this specific aspect\n"
    
    if focus_areas:
        base_prompt += f"\n\n### FOCUS AREAS\nPay special attention to: {', '.join(focus_areas)}\n"
    
    if depth == "comprehensive":
        base_prompt += "\n\nProvide MAXIMUM detail in every section. The detailed description should be 400-500 words."
    elif depth == "detailed":
        base_prompt += "\n\nProvide thorough detail in all sections. The detailed description should be 200-300 words."
    elif depth == "standard":
        base_prompt += "\n\nProvide standard detail. The detailed description should be 100-150 words."
    else:  # brief
        base_prompt += "\n\nKeep it concise but cover all sections. The detailed description should be 50-100 words."
    
    base_prompt += """

FORMAT YOUR RESPONSE AS VALID JSON matching this structure:
{
    "title": "string",
    "short_description": "string",
    "detailed_description": "string (100-500 words)",
    "scene_type": "indoor|outdoor|urban|nature|beach|mountain|studio|home|office|restaurant|event|street|other",
    "scene_setting": "string",
    "indoor_outdoor": "indoor|outdoor|mixed",
    "location_type": "string",
    "location_guess": "string or null",
    "environment_description": "string",
    "weather_conditions": "string or null",
    "time_of_day": "dawn|morning|midday|afternoon|evening|sunset|night|unknown",
    "time_indicators": ["string"],
    "season_guess": "string or null",
    "people_count": number,
    "people": [
        {
            "person_id": number,
            "position": "string",
            "approximate_age": "string",
            "gender_presentation": "string",
            "clothing_description": "string",
            "clothing_style": "string",
            "clothing_colors": ["string"],
            "accessories": ["string"],
            "facial_expression": "string",
            "primary_emotion": "happy|sad|angry|surprised|neutral|excited|thoughtful|confident|relaxed|focused",
            "secondary_emotion": "string or null",
            "emotion_confidence": number 0-1,
            "body_pose": "string",
            "apparent_action": "string",
            "gaze_direction": "string",
            "notable_features": ["string"]
        }
    ],
    "group_dynamics": "string or null",
    "main_subjects": ["string"],
    "objects_detected": [{"name": "string", "category": "string", "position": "string", "prominence": "string"}],
    "background_elements": ["string"],
    "foreground_elements": ["string"],
    "dominant_colors": ["string"],
    "color_palette": "string",
    "lighting_type": "string",
    "lighting_quality": "string",
    "contrast_level": "low|medium|high",
    "composition_style": "string",
    "focal_point": "string",
    "depth_of_field": "shallow|medium|deep",
    "perspective": "string",
    "overall_mood": "string",
    "visual_style": "string",
    "aesthetic_tags": ["string"],
    "content_type": "string",
    "content_category": "string",
    "suitable_platforms": ["string"],
    "visible_text": ["string"],
    "brand_logos": ["string"],
    "suggested_hashtags": ["string"],
    "suggested_caption": "string",
    "engagement_prediction": "low|medium|high",
    "image_quality": "string",
    "sharpness": "string",
    "exposure": "string",
    "custom_fields": {},
    "overall_confidence": number 0-1
}"""
    
    return base_prompt


async def analyze_with_openai(image_data: str, is_url: bool, custom_fields: List[str], focus_areas: List[str], depth: str) -> Dict[str, Any]:
    """Analyze image using OpenAI Vision API"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    prompt = get_analysis_prompt(custom_fields, focus_areas, depth)
    
    if is_url:
        image_content = {"type": "image_url", "image_url": {"url": image_data}}
    else:
        image_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_content,
                        ],
                    }
                ],
                "max_tokens": 4096,
            },
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"OpenAI API error: {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Try to parse JSON from response
        try:
            # Find JSON in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Return raw content if JSON parsing fails
        return {"raw_analysis": content}


async def analyze_with_mock(custom_fields: List[str]) -> Dict[str, Any]:
    """Generate mock analysis for testing"""
    import random
    
    emotions = ["happy", "confident", "relaxed", "focused", "excited"]
    times = ["morning", "afternoon", "evening", "sunset"]
    scenes = ["outdoor", "indoor", "urban", "nature", "studio"]
    
    mock_result = {
        "title": "Dynamic Urban Street Portrait",
        "short_description": "A confident young professional captured in a vibrant city setting during golden hour.",
        "detailed_description": """This striking image captures a moment of urban elegance against the backdrop of a bustling city street. The subject, a young professional in their late twenties, stands confidently in the center of the frame, their presence commanding attention while the city life flows around them.

The warm golden hour light bathes the scene in a flattering glow, creating soft shadows and highlights that add depth and dimension to the composition. Behind them, the urban landscape unfolds with characteristic elements: modern architecture with glass facades reflecting the evening sky, street lamps just beginning to flicker on, and the subtle blur of pedestrians going about their evening routines.

The subject's attire speaks to contemporary urban fashion - a well-fitted blazer in charcoal gray paired with a crisp white shirt, the collar casually open. Their posture exudes confidence, with shoulders back and a slight forward lean that suggests purpose and determination. The facial expression is engaging, featuring a genuine smile that reaches their eyes, conveying warmth and approachability despite the sophisticated setting.

Notable compositional choices include the use of leading lines from the street and buildings that draw the eye toward the subject, while the shallow depth of field creates a pleasing separation between subject and background. The color palette harmonizes warm skin tones with cool urban grays and blues, punctuated by the golden light that unifies the entire scene.

This image would excel on professional networking platforms or lifestyle content, effectively communicating success, approachability, and urban sophistication in equal measure.""",
        "scene_type": random.choice(scenes),
        "scene_setting": "Urban street with modern buildings",
        "indoor_outdoor": "outdoor",
        "location_type": "City downtown area",
        "location_guess": "Could be New York, Chicago, or similar metropolitan area",
        "environment_description": "Modern urban environment with glass buildings, street lights, and pedestrian activity",
        "weather_conditions": "Clear sky, warm conditions",
        "time_of_day": random.choice(times),
        "time_indicators": ["Golden hour lighting", "Street lamps not yet on", "Long shadows"],
        "season_guess": "Late spring or early fall",
        "people_count": 1,
        "people": [
            {
                "person_id": 1,
                "position": "center",
                "approximate_age": "25-30",
                "gender_presentation": "masculine",
                "clothing_description": "Charcoal gray fitted blazer over a crisp white button-up shirt with collar open. Dark slim-fit trousers visible.",
                "clothing_style": "Smart casual / Business casual",
                "clothing_colors": ["charcoal gray", "white", "dark navy"],
                "accessories": ["Silver wristwatch", "Leather messenger bag visible at side"],
                "facial_expression": "Warm, genuine smile with slight squint from sunlight",
                "primary_emotion": random.choice(emotions),
                "secondary_emotion": "happy",
                "emotion_confidence": 0.87,
                "body_pose": "Standing upright with slight forward lean, shoulders back",
                "apparent_action": "Posing for photo while pausing on urban walk",
                "gaze_direction": "Directly at camera with slight head tilt",
                "notable_features": ["Well-groomed facial hair", "Confident stance", "Professional appearance"]
            }
        ],
        "group_dynamics": None,
        "main_subjects": ["Young professional", "Urban setting", "Golden hour portrait"],
        "objects_detected": [
            {"name": "Messenger bag", "category": "Accessory", "position": "Subject's side", "prominence": "foreground"},
            {"name": "Street lamp", "category": "Infrastructure", "position": "Background left", "prominence": "background"},
            {"name": "Modern building", "category": "Architecture", "position": "Background", "prominence": "background"},
        ],
        "background_elements": ["Glass office buildings", "Street lamps", "Blurred pedestrians", "Urban skyline"],
        "foreground_elements": ["Subject", "Partial view of messenger bag"],
        "dominant_colors": ["Charcoal gray", "Golden/amber", "White", "Blue-gray", "Warm skin tones"],
        "color_palette": "Warm with cool urban accents",
        "lighting_type": "Natural golden hour",
        "lighting_quality": "Soft and flattering",
        "contrast_level": "medium",
        "composition_style": "Rule of thirds with centered subject",
        "focal_point": "Subject's face and expression",
        "depth_of_field": "shallow",
        "perspective": "Eye level, slightly below",
        "overall_mood": "Confident, aspirational, warm",
        "visual_style": "Contemporary lifestyle photography",
        "aesthetic_tags": ["urban", "professional", "golden hour", "lifestyle", "portrait", "modern", "confident", "city life", "fashion forward", "aspirational"],
        "content_type": "Portrait / Lifestyle",
        "content_category": "Professional / Fashion / Lifestyle",
        "suitable_platforms": ["LinkedIn", "Instagram", "Twitter", "Professional website"],
        "visible_text": [],
        "brand_logos": [],
        "suggested_hashtags": ["#urbanportrait", "#goldenhour", "#citylife", "#professionalstyle", "#streetstyle", "#portraitphotography", "#businesscasual", "#mensfashion", "#lifestylephotography", "#urbanfashion", "#confident", "#success", "#downtownvibes", "#eveninglight", "#modernprofessional"],
        "suggested_caption": "Finding my stride in the urban jungle. There's something magical about the city at golden hour - when ambition meets opportunity and every street corner holds potential. ✨ #CityLife #GoldenHour",
        "engagement_prediction": "high",
        "image_quality": "Excellent - professional grade",
        "sharpness": "Sharp focus on subject with pleasing background blur",
        "exposure": "Well-exposed with good dynamic range",
        "custom_fields": {field: f"Analysis for {field}" for field in custom_fields},
        "overall_confidence": 0.92,
    }
    
    return mock_result


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=ImageAnalysisResult)
async def analyze_image(request: AnalysisRequest):
    """
    Analyze an image with comprehensive AI analysis.
    Provide either image_url or image_base64.
    """
    import time
    start_time = time.time()
    
    if not request.image_url and not request.image_base64:
        raise HTTPException(status_code=400, detail="Either image_url or image_base64 is required")
    
    try:
        # Check if OpenAI key exists
        if os.getenv("OPENAI_API_KEY"):
            if request.image_url:
                analysis_data = await analyze_with_openai(
                    request.image_url, 
                    is_url=True,
                    custom_fields=request.custom_fields,
                    focus_areas=request.focus_areas,
                    depth=request.analysis_depth,
                )
            else:
                analysis_data = await analyze_with_openai(
                    request.image_base64,
                    is_url=False,
                    custom_fields=request.custom_fields,
                    focus_areas=request.focus_areas,
                    depth=request.analysis_depth,
                )
        else:
            # Use mock for demo
            analysis_data = await analyze_with_mock(request.custom_fields)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Create result object
        analysis_id = str(uuid.uuid4())
        
        # Map the data to our model
        result = ImageAnalysisResult(
            analysis_id=analysis_id,
            image_url=request.image_url,
            processing_time_ms=processing_time,
            **{k: v for k, v in analysis_data.items() if k in ImageAnalysisResult.__fields__}
        )
        
        # Store for later retrieval
        analyses_store[analysis_id] = result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-upload")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    custom_fields: str = Form(default=""),
    focus_areas: str = Form(default=""),
    analysis_depth: str = Form(default="detailed"),
):
    """
    Analyze an uploaded image file.
    """
    import time
    start_time = time.time()
    
    # Read and encode file
    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode("utf-8")
    
    custom_fields_list = [f.strip() for f in custom_fields.split(",") if f.strip()]
    focus_areas_list = [f.strip() for f in focus_areas.split(",") if f.strip()]
    
    try:
        if os.getenv("OPENAI_API_KEY"):
            analysis_data = await analyze_with_openai(
                image_base64,
                is_url=False,
                custom_fields=custom_fields_list,
                focus_areas=focus_areas_list,
                depth=analysis_depth,
            )
        else:
            analysis_data = await analyze_with_mock(custom_fields_list)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        analysis_id = str(uuid.uuid4())
        
        result = ImageAnalysisResult(
            analysis_id=analysis_id,
            processing_time_ms=processing_time,
            **{k: v for k, v in analysis_data.items() if k in ImageAnalysisResult.__fields__}
        )
        
        analyses_store[analysis_id] = result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analysis/{analysis_id}", response_model=ImageAnalysisResult)
async def get_analysis(analysis_id: str):
    """Retrieve a previous analysis by ID"""
    if analysis_id not in analyses_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analyses_store[analysis_id]


@router.get("/analyses")
async def list_analyses(limit: int = 20):
    """List recent analyses"""
    analyses = list(analyses_store.values())
    analyses.sort(key=lambda x: x.analyzed_at, reverse=True)
    return {"analyses": analyses[:limit]}


@router.get("/fields")
async def get_available_fields():
    """Get list of all analysis fields"""
    return {
        "standard_fields": [
            "title", "short_description", "detailed_description",
            "scene_type", "scene_setting", "location_type", "time_of_day",
            "people_count", "people_analysis", "objects_detected",
            "dominant_colors", "color_palette", "lighting_type",
            "composition_style", "overall_mood", "visual_style",
            "content_type", "suggested_hashtags", "suggested_caption",
            "image_quality", "engagement_prediction"
        ],
        "person_fields": [
            "approximate_age", "gender_presentation", "clothing_description",
            "clothing_style", "clothing_colors", "accessories",
            "facial_expression", "primary_emotion", "secondary_emotion",
            "body_pose", "apparent_action", "gaze_direction", "notable_features"
        ],
        "custom_field_examples": [
            "brand_alignment", "product_visibility", "call_to_action",
            "target_demographic", "cultural_relevance", "controversy_check",
            "accessibility_notes", "copyright_concerns", "model_release_needed"
        ],
        "focus_area_examples": [
            "fashion", "emotions", "background", "colors", "composition",
            "text", "brands", "products", "people", "architecture"
        ],
        "analysis_depths": ["brief", "standard", "detailed", "comprehensive"]
    }
