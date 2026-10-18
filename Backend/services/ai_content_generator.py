"""
AI Content Generator Service
Generates content using various AI providers (OpenAI, Anthropic, Stability, Runway, etc.)
"""
import json
import logging
import os
from typing import Dict, List, Any, Optional
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a required AI provider API key is missing."""
    pass


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STABILITY = "stability"
    RUNWAY = "runway"
    MIDJOURNEY = "midjourney"
    DALL_E = "dalle"


class AIContentGenerator:
    """
    Generates content using various AI providers

    Supports:
    - Text generation (blog posts, captions)
    - Image generation (carousels, graphics)
    - Video generation
    - Content variations
    """

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.stability_key = os.getenv("STABILITY_API_KEY")
        self.runway_key = os.getenv("RUNWAY_API_KEY")

    def _require_key(self, provider: AIProvider) -> str:
        """Validate that an API key is configured for the given provider."""
        key_map = {
            AIProvider.OPENAI: ("OPENAI_API_KEY", self.openai_key),
            AIProvider.ANTHROPIC: ("ANTHROPIC_API_KEY", self.anthropic_key),
            AIProvider.STABILITY: ("STABILITY_API_KEY", self.stability_key),
            AIProvider.RUNWAY: ("RUNWAY_API_KEY", self.runway_key),
            AIProvider.DALL_E: ("OPENAI_API_KEY", self.openai_key),
        }
        env_var, key = key_map.get(provider, (None, None))
        if not key:
            raise ProviderNotConfiguredError(
                f"{provider.value} provider not configured: "
                f"set the {env_var} environment variable"
            )
        return key

    async def generate_blog_post(
        self,
        topic: str,
        length: str = "medium",  # short, medium, long
        tone: str = "professional",
        provider: AIProvider = AIProvider.OPENAI
    ) -> Dict[str, Any]:
        """
        Generate a blog post using AI

        Returns:
            Dict with title, body, summary, keywords
        """
        if provider == AIProvider.OPENAI:
            self._require_key(AIProvider.OPENAI)
            return await self._generate_with_openai(
                prompt=f"Write a {length} {tone} blog post about: {topic}",
                content_type="blog"
            )
        elif provider == AIProvider.ANTHROPIC:
            self._require_key(AIProvider.ANTHROPIC)
            return await self._generate_with_anthropic(
                prompt=f"Write a {length} {tone} blog post about: {topic}",
                content_type="blog"
            )
        else:
            raise ProviderNotConfiguredError(
                f"Provider '{provider.value}' does not support blog post generation. "
                f"Use 'openai' or 'anthropic'."
            )

    async def generate_carousel_images(
        self,
        prompt: str,
        slide_count: int = 5,
        style: str = "modern",
        provider: AIProvider = AIProvider.STABILITY
    ) -> List[Dict[str, Any]]:
        """
        Generate carousel images using AI

        Returns:
            List of image URLs and metadata
        """
        images = []

        for i in range(slide_count):
            slide_prompt = f"{prompt}, slide {i+1} of {slide_count}, {style} style"

            if provider == AIProvider.STABILITY:
                self._require_key(AIProvider.STABILITY)
                image_url = await self._generate_image_stability(slide_prompt)
            elif provider == AIProvider.DALL_E:
                self._require_key(AIProvider.DALL_E)
                image_url = await self._generate_image_dalle(slide_prompt)
            else:
                raise ProviderNotConfiguredError(
                    f"Provider '{provider.value}' does not support image generation. "
                    f"Use 'stability' or 'dalle'."
                )

            images.append({
                "url": image_url,
                "slide_number": i + 1,
                "prompt": slide_prompt,
                "provider": provider.value
            })

        return images

    async def generate_video(
        self,
        prompt: str,
        duration: int = 15,  # seconds
        style: str = "cinematic",
        provider: AIProvider = AIProvider.RUNWAY
    ) -> Dict[str, Any]:
        """
        Generate video using AI

        Returns:
            Dict with video URL and metadata
        """
        if provider == AIProvider.RUNWAY:
            self._require_key(AIProvider.RUNWAY)
            return await self._generate_video_runway(prompt, duration, style)
        else:
            raise ProviderNotConfiguredError(
                f"Provider '{provider.value}' does not support video generation. "
                f"Use 'runway'."
            )

    async def generate_text_overlay(
        self,
        base_text: str,
        style: str = "bold",
        font_size: int = 48
    ) -> Dict[str, Any]:
        """
        Generate text overlay configuration for words-on-video

        Returns:
            Dict with text styling and positioning
        """
        return {
            "text": base_text,
            "style": style,
            "font_size": font_size,
            "position": "center",
            "color": "#FFFFFF",
            "background": "rgba(0,0,0,0.5)",
            "animation": "fade_in"
        }

    # Private methods for provider-specific implementations

    async def _generate_with_openai(
        self,
        prompt: str,
        content_type: str
    ) -> Dict[str, Any]:
        """Generate content using OpenAI GPT API."""
        system_prompt = (
            f"You are a content creator assistant. Generate a {content_type}. "
            "Respond with valid JSON containing: title, body, summary, keywords (array)."
        )

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        result["provider"] = "openai"
        return result

    async def _generate_with_anthropic(
        self,
        prompt: str,
        content_type: str
    ) -> Dict[str, Any]:
        """Generate content using Anthropic Claude API."""
        system_prompt = (
            f"You are a content creator assistant. Generate a {content_type}. "
            "Respond with valid JSON containing: title, body, summary, keywords (array). "
            "Output ONLY the JSON object, no other text."
        )

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data["content"][0]["text"]
        result = json.loads(content)
        result["provider"] = "anthropic"
        return result

    async def _generate_image_stability(self, prompt: str) -> str:
        """Generate image using Stability AI API."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.stability_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [{"text": prompt, "weight": 1.0}],
                    "cfg_scale": 7,
                    "height": 1024,
                    "width": 1024,
                    "steps": 30,
                    "samples": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

        # Stability returns base64-encoded images in artifacts array
        artifact = data["artifacts"][0]
        # Return the base64 data URI for downstream processing
        return f"data:image/png;base64,{artifact['base64']}"

    async def _generate_image_dalle(self, prompt: str) -> str:
        """Generate image using DALL-E 3 API."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard",
                },
            )
            response.raise_for_status()
            data = response.json()

        return data["data"][0]["url"]

    async def _generate_video_runway(
        self, prompt: str, duration: int, style: str
    ) -> Dict[str, Any]:
        """Generate video using Runway ML Gen-3 API."""
        async with httpx.AsyncClient(timeout=300) as client:
            # Start generation
            response = await client.post(
                "https://api.dev.runwayml.com/v1/image_to_video",
                headers={
                    "Authorization": f"Bearer {self.runway_key}",
                    "Content-Type": "application/json",
                    "X-Runway-Version": "2024-11-06",
                },
                json={
                    "promptText": f"{prompt}, {style} style",
                    "model": "gen3a_turbo",
                    "duration": min(duration, 10),  # Runway max 10s
                    "watermark": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        task_id = data.get("id")
        return {
            "task_id": task_id,
            "duration": duration,
            "prompt": prompt,
            "style": style,
            "provider": "runway",
            "status": "processing",
        }
