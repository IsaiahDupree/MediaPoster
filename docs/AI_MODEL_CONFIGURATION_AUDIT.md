# AI Model Configuration Audit & Redesign
**Date:** 2025-12-27  
**Purpose:** Audit current model usage and design configurable swapping system

---

## Current State Audit

### Services Using AI Models

#### 1. VideoAnalyzer (`services/video_analyzer.py`)
**Current:**
```python
groq_key = os.getenv("GROQ_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
self.transcriber = WhisperTranscriber(api_key=groq_key, provider="groq")
self.content_analyzer = ContentAnalyzer(api_key=groq_key)
self.frame_analyzer = FrameAnalyzer(api_key=groq_key)
```
**Issues:**
- Hardcoded provider selection logic
- No way to configure models per task
- Passes same API key to all services

#### 2. WhisperTranscriber (`services/whisper_transcriber.py`)
**Current:**
```python
model_name = "whisper-large-v3" if self.provider == "groq" else "whisper-1"
```
**Issues:**
- Hardcoded model names
- No configuration for model selection

#### 3. ContentAnalyzer (`services/content_analyzer.py`)
**Current:**
```python
model="gpt-4-turbo-preview"  # Hardcoded
```
**Issues:**
- Hardcoded to GPT-4 Turbo
- No way to use Groq or other providers
- Expensive ($10/$30 per MTok)

#### 4. FrameAnalyzer (`services/frame_analyzer.py`)
**Current:**
```python
model="gpt-4o"  # Hardcoded
```
**Issues:**
- Hardcoded to GPT-4o
- Should use GPT-4o Mini for cost savings
- No provider flexibility

#### 5. ThumbnailGenerator
**Current:**
- Uses OpenAI GPT-4
**Issues:**
- Should use Groq for FREE

#### 6. HashtagGenerator
**Current:**
- Uses OpenAI GPT-3.5/GPT-4
**Issues:**
- Should use Groq for FREE

---

## Problems with Current Architecture

### 1. **No Centralized Configuration**
- Each service hardcodes its model choice
- No single place to configure models
- Difficult to test different models

### 2. **No Provider Abstraction**
- Services directly use OpenAI/Groq clients
- Can't easily swap providers
- Tight coupling to specific APIs

### 3. **No Task-Based Selection**
- Can't configure different models for different tasks
- Can't optimize cost vs quality per use case

### 4. **No Environment-Based Config**
- Can't easily switch models via environment variables
- Requires code changes to test new models

---

## Proposed Architecture

### 1. Centralized Model Registry

```python
# config/model_registry.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaskType(str, Enum):
    TRANSCRIPTION = "transcription"
    CONTENT_ANALYSIS = "content_analysis"
    FRAME_ANALYSIS = "frame_analysis"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    HASHTAG_GENERATION = "hashtag_generation"
    COMMENT_GENERATION = "comment_generation"
    SUMMARIZATION = "summarization"
    EMBEDDINGS = "embeddings"

@dataclass
class ModelConfig:
    provider: str  # "openai", "groq", "anthropic", "google"
    model: str
    api_key_env: str
    cost_input: float  # per MTok
    cost_output: float
    max_tokens: int = 4096
    temperature: float = 0.7

class ModelRegistry:
    """Central registry for all AI models"""
    
    # Default model configurations per task
    MODELS = {
        TaskType.TRANSCRIPTION: ModelConfig(
            provider="groq",
            model="whisper-large-v3",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0
        ),
        TaskType.CONTENT_ANALYSIS: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=2048
        ),
        TaskType.FRAME_ANALYSIS: ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            cost_input=0.15,
            cost_output=0.60,
            max_tokens=1024
        ),
        TaskType.THUMBNAIL_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0
        ),
        TaskType.HASHTAG_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=256
        )
    }
    
    @classmethod
    def get_model_config(cls, task: TaskType) -> ModelConfig:
        """Get model configuration for a task"""
        # Check for environment override
        env_key = f"{task.value.upper()}_MODEL"
        if os.getenv(env_key):
            return cls._parse_env_config(task, os.getenv(env_key))
        
        return cls.MODELS.get(task)
    
    @classmethod
    def _parse_env_config(cls, task: TaskType, config_str: str) -> ModelConfig:
        """Parse model config from environment variable"""
        # Format: "provider:model" e.g., "openai:gpt-4o-mini"
        provider, model = config_str.split(":")
        
        # Get API key for provider
        api_key_env = f"{provider.upper()}_API_KEY"
        
        # Return custom config
        return ModelConfig(
            provider=provider,
            model=model,
            api_key_env=api_key_env,
            cost_input=0.0,  # Would need lookup
            cost_output=0.0
        )
```

### 2. Unified AI Client

```python
# services/ai_client.py

class AIClient:
    """Unified client for all AI providers"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize provider-specific client"""
        api_key = os.getenv(self.config.api_key_env)
        
        if self.config.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        
        elif self.config.provider == "groq":
            from groq import Groq
            return Groq(api_key=api_key)
        
        elif self.config.provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(api_key=api_key)
        
        elif self.config.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return genai
        
        raise ValueError(f"Unknown provider: {self.config.provider}")
    
    def chat_completion(self, messages: list, **kwargs) -> str:
        """Unified chat completion interface"""
        
        if self.config.provider in ["openai", "groq"]:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens)
            )
            return response.choices[0].message.content
        
        elif self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens)
            )
            return response.content[0].text
        
        # Add other providers...
    
    def transcribe(self, audio_path: str) -> dict:
        """Unified transcription interface"""
        
        with open(audio_path, "rb") as audio_file:
            if self.config.provider in ["openai", "groq"]:
                response = self.client.audio.transcriptions.create(
                    model=self.config.model,
                    file=audio_file,
                    response_format="verbose_json"
                )
                return {
                    "text": response.text,
                    "language": response.language,
                    "duration": response.duration
                }
        
        raise NotImplementedError(f"Transcription not supported for {self.config.provider}")
```

### 3. Updated Services

```python
# services/video_analyzer.py (NEW)

class VideoAnalyzer:
    def __init__(self):
        # Get model configs from registry
        transcription_config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)
        analysis_config = ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)
        frame_config = ModelRegistry.get_model_config(TaskType.FRAME_ANALYSIS)
        
        # Initialize unified clients
        self.transcription_client = AIClient(transcription_config)
        self.analysis_client = AIClient(analysis_config)
        self.frame_client = AIClient(frame_config)
        
        logger.info(f"VideoAnalyzer initialized:")
        logger.info(f"  Transcription: {transcription_config.provider}/{transcription_config.model}")
        logger.info(f"  Analysis: {analysis_config.provider}/{analysis_config.model}")
        logger.info(f"  Frames: {frame_config.provider}/{frame_config.model}")
```

---

## Configuration Options

### Environment Variables

```bash
# Default (uses registry defaults)
GROQ_API_KEY=...
OPENAI_API_KEY=...

# Override specific tasks
TRANSCRIPTION_MODEL=groq:whisper-large-v3
CONTENT_ANALYSIS_MODEL=groq:llama-3.3-70b-versatile
FRAME_ANALYSIS_MODEL=openai:gpt-4o-mini
THUMBNAIL_GENERATION_MODEL=groq:llama-3.3-70b-versatile
HASHTAG_GENERATION_MODEL=groq:llama-3.1-8b-instant

# Or use different providers
CONTENT_ANALYSIS_MODEL=anthropic:claude-3-5-sonnet
FRAME_ANALYSIS_MODEL=google:gemini-1.5-flash
```

### Configuration File

```yaml
# config/models.yaml
models:
  transcription:
    provider: groq
    model: whisper-large-v3
    
  content_analysis:
    provider: groq
    model: llama-3.3-70b-versatile
    temperature: 0.7
    max_tokens: 2048
    
  frame_analysis:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.5
    max_tokens: 1024
```

---

## Benefits

### 1. **Easy Model Swapping**
```bash
# Test different models without code changes
CONTENT_ANALYSIS_MODEL=anthropic:claude-3-5-sonnet
FRAME_ANALYSIS_MODEL=google:gemini-1.5-flash
```

### 2. **Cost Optimization**
- Configure cheap models for batch processing
- Use expensive models only when needed

### 3. **A/B Testing**
- Easy to compare model performance
- Track costs per model

### 4. **Provider Independence**
- Not locked into one provider
- Can switch if pricing changes

### 5. **Centralized Management**
- One place to see all model usage
- Easy to audit costs

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `ModelRegistry` class
2. Create `AIClient` unified interface
3. Add environment variable support

### Phase 2: Update Services
1. Update `VideoAnalyzer` to use registry
2. Update `ContentAnalyzer` to use registry
3. Update `FrameAnalyzer` to use registry

### Phase 3: Testing
1. Test with 1 video using new system
2. Verify all models work correctly
3. Compare costs

### Phase 4: Rollout
1. Update all remaining services
2. Document configuration options
3. Deploy to production

---

## Next Steps

1. **Implement ModelRegistry** - Central configuration
2. **Implement AIClient** - Unified interface
3. **Test with 1 video** - Verify it works
4. **Update remaining services** - Full rollout
