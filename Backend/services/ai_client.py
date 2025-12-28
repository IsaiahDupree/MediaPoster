"""
AI Client - Unified interface for all AI providers
Abstracts provider-specific APIs into a common interface
"""
import os
from typing import List, Dict, Any, Optional
from loguru import logger

from config.model_registry import ModelConfig, ModelRegistry


class AIClient:
    """
    Unified client for all AI providers
    
    Usage:
        from config.model_registry import TaskType, ModelRegistry
        from services.ai_client import AIClient
        
        config = ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)
        client = AIClient(config)
        
        response = client.chat_completion([
            {"role": "user", "content": "Analyze this video..."}
        ])
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize AI client with model configuration
        
        Args:
            config: ModelConfig from ModelRegistry
        """
        self.config = config
        self.client = self._init_client()
        
        logger.info(f"AIClient initialized: {config.provider}/{config.model}")
    
    def _init_client(self):
        """Initialize provider-specific client"""
        api_key = os.getenv(self.config.api_key_env)
        
        if not api_key:
            raise ValueError(f"{self.config.api_key_env} not found in environment")
        
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
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Unified chat completion interface
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Response text from model
        """
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        try:
            if self.config.provider in ["openai", "groq"]:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content
            
            elif self.config.provider == "anthropic":
                # Anthropic uses different message format
                system_messages = [m for m in messages if m["role"] == "system"]
                user_messages = [m for m in messages if m["role"] != "system"]
                
                system_prompt = system_messages[0]["content"] if system_messages else None
                
                response = self.client.messages.create(
                    model=self.config.model,
                    messages=user_messages,
                    system=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response.content[0].text
            
            elif self.config.provider == "google":
                # Google Gemini format
                model = self.client.GenerativeModel(self.config.model)
                
                # Convert messages to Gemini format
                prompt_parts = []
                for msg in messages:
                    role = "user" if msg["role"] in ["user", "system"] else "model"
                    prompt_parts.append({"role": role, "parts": [msg["content"]]})
                
                response = model.generate_content(
                    prompt_parts,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens
                    }
                )
                return response.text
            
            raise NotImplementedError(f"Chat completion not implemented for {self.config.provider}")
            
        except Exception as e:
            logger.error(f"Chat completion failed ({self.config.provider}/{self.config.model}): {e}")
            raise
    
    def transcribe(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Unified transcription interface
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: "en")
        
        Returns:
            Dict with transcript and metadata
        """
        if self.config.provider not in ["openai", "groq"]:
            raise NotImplementedError(f"Transcription not supported for {self.config.provider}")
        
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.config.model,
                    file=audio_file,
                    response_format="verbose_json",
                    language=language
                )
                
                return {
                    "text": response.text,
                    "language": response.language,
                    "duration": response.duration,
                    "segments": response.segments if hasattr(response, 'segments') else []
                }
        
        except Exception as e:
            logger.error(f"Transcription failed ({self.config.provider}/{self.config.model}): {e}")
            raise
    
    def vision_analysis(
        self,
        image_path: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Unified vision/image analysis interface
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
        
        Returns:
            Analysis text from model
        """
        if self.config.provider not in ["openai", "google", "anthropic"]:
            raise NotImplementedError(f"Vision analysis not supported for {self.config.provider}")
        
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        try:
            if self.config.provider == "openai":
                import base64
                
                # Encode image to base64
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            
            elif self.config.provider == "google":
                import PIL.Image
                
                model = self.client.GenerativeModel(self.config.model)
                image = PIL.Image.open(image_path)
                
                response = model.generate_content(
                    [prompt, image],
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens
                    }
                )
                return response.text
            
            elif self.config.provider == "anthropic":
                import base64
                
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                response = self.client.messages.create(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.content[0].text
            
            raise NotImplementedError(f"Vision analysis not implemented for {self.config.provider}")
            
        except Exception as e:
            logger.error(f"Vision analysis failed ({self.config.provider}/{self.config.model}): {e}")
            raise
    
    def embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        if self.config.provider != "openai":
            raise NotImplementedError(f"Embeddings not supported for {self.config.provider}")
        
        try:
            response = self.client.embeddings.create(
                model=self.config.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        
        except Exception as e:
            logger.error(f"Embeddings failed ({self.config.provider}/{self.config.model}): {e}")
            raise


# Convenience functions
def create_client_for_task(task_type) -> AIClient:
    """
    Create AIClient for a specific task
    
    Args:
        task_type: TaskType enum value
    
    Returns:
        Configured AIClient instance
    """
    from config.model_registry import ModelRegistry
    config = ModelRegistry.get_model_config(task_type)
    return AIClient(config)
