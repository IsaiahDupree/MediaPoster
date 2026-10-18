"""
TikTok Captcha Solver Service

This module provides integration with the RapidAPI TikTok Captcha Solver service.
Supports all 4 TikTok captcha types: Whirl, Slide, 3D, and Icon.
"""

import os
import base64
import asyncio
import aiohttp
from typing import Dict, Optional, Literal, Union
from pathlib import Path
from loguru import logger
from PIL import Image
import io


CaptchaType = Literal["whirl", "slide", "3d", "icon"]


class TikTokCaptchaSolver:
    """
    Service for solving TikTok captchas using RapidAPI TikTok Captcha Solver.
    
    Supports:
    - Whirl (Rotate) captchas
    - Slide (Puzzle) captchas  
    - 3D (Two same objects) captchas
    - Icon (Correct objects) captchas
    """
    
    VALID_CAPTCHA_TYPES = ["puzzle", "whirl", "3d"]
    
    def __init__(self):
        """Initialize the captcha solver with API credentials from environment."""
        self.api_url = os.getenv("TIKTOK_CAPTCHA_API_URL", "https://tiktok-captcha-solver2.p.rapidapi.com")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.rapidapi_host = os.getenv("RAPIDAPI_HOST", "tiktok-captcha-solver2.p.rapidapi.com")
        
        if not self.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not found in environment variables")
        
        self.headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": self.rapidapi_host,
            "x-rapidapi-key": self.rapidapi_key
        }
        
        logger.info(f"TikTok Captcha Solver initialized with API URL: {self.api_url}")
    
    @staticmethod
    def image_to_base64(image_path: Union[str, Path]) -> str:
        """
        Convert an image file to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    @staticmethod
    def pil_image_to_base64(image: Image.Image) -> str:
        """
        Convert a PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded string of the image
        """
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def _process_image(self, image_source: Union[str, Path, Image.Image]) -> str:
        """
        Process image source to base64 string or URL.
        
        Args:
            image_source: URL, file path, or PIL Image
            
        Returns:
            String containing URL or base64 data URI
        """
        if isinstance(image_source, str) and (image_source.startswith("http://") or image_source.startswith("https://")):
            logger.info(f"Using captcha image URL: {image_source[:50]}...")
            return image_source
        elif isinstance(image_source, Image.Image):
            logger.info("Using PIL Image converted to base64")
            return f"data:image/png;base64,{self.pil_image_to_base64(image_source)}"
        else:
            logger.info(f"Using local image file: {image_source}")
            return f"data:image/png;base64,{self.image_to_base64(image_source)}"

    async def _make_api_request(self, url: str, payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        Make API request with retries.
        
        Args:
            url: API endpoint URL
            payload: Request payload
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response dictionary
        """
        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            try:
                                result = await response.json(content_type=None)
                                logger.success(f"Captcha solved successfully: {result}")
                                return result
                            except Exception as e:
                                logger.error(f"Failed to parse JSON response: {e}")
                                logger.debug(f"Response text: {response_text}")
                                raise
                        else:
                            logger.error(f"API error (attempt {attempt}/{max_retries}): {response.status} - {response_text}")
                            
                            if attempt < max_retries:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            else:
                                raise aiohttp.ClientError(
                                    f"Failed to solve captcha after {max_retries} attempts. "
                                    f"Status: {response.status}, Response: {response_text}"
                                )
            
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            
            except aiohttp.ClientError as e:
                logger.error(f"Client error (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    
    async def solve_captcha(
        self,
        captcha_type: CaptchaType,
        image_source: Union[str, Path, Image.Image],
        width: int,
        height: int,
        version: str = "2",
        proxy: str = "",
        max_retries: int = 3
    ) -> Dict:
        """
        Solve a TikTok captcha using the RapidAPI service.
        
        Args:
            captcha_type: Type of captcha ("whirl", "slide", "3d", "icon")
            image_source: Either a URL string, file path, or PIL Image
            width: Width of the captcha image in pixels
            height: Height of the captcha image in pixels
            version: Captcha version (default "2")
            proxy: Optional proxy configuration
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing the solution response from the API
            
        Raises:
            ValueError: If captcha_type is invalid
            aiohttp.ClientError: If API request fails
        """
        if captcha_type not in self.endpoints:
            raise ValueError(f"Invalid captcha type: {captcha_type}. Must be one of {list(self.endpoints.keys())}")
        
        # Prepare image data
        if isinstance(image_source, str) and (image_source.startswith("http://") or image_source.startswith("https://")):
            # It's a URL
            b64_or_url = image_source
            logger.info(f"Using captcha image URL: {image_source[:50]}...")
        elif isinstance(image_source, Image.Image):
            # It's a PIL Image
            b64_or_url = f"data:image/png;base64,{self.pil_image_to_base64(image_source)}"
            logger.info("Using PIL Image converted to base64")
        else:
            # It's a file path
            b64_or_url = f"data:image/png;base64,{self.image_to_base64(image_source)}"
            logger.info(f"Using local image file: {image_source}")
        
        # Prepare request payload
        param_name = "b64Internal_or_url" if captcha_type == "whirl" else "b64External_or_url"
        
        payload = {
            param_name: b64_or_url,
            "width": str(width),
            "height": str(height),
            "version": version,
            "proxy": proxy
        }
        
        endpoint = self.endpoints[captcha_type]
        logger.info(f"Solving {captcha_type} captcha at endpoint: {endpoint}")
        
        # Attempt the API request with retries
        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        json=payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            try:
                                result = await response.json(content_type=None)
                                logger.success(f"Captcha solved successfully: {result}")
                                return result
                            except Exception as e:
                                logger.error(f"Failed to parse JSON response: {e}")
                                logger.debug(f"Response text: {response_text}")
                                raise
                        else:
                            logger.error(f"API error (attempt {attempt}/{max_retries}): {response.status} - {response_text}")
                            
                            if attempt < max_retries:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            else:
                                raise aiohttp.ClientError(
                                    f"Failed to solve captcha after {max_retries} attempts. "
                                    f"Status: {response.status}, Response: {response_text}"
                                )
            
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            
            except aiohttp.ClientError as e:
                logger.error(f"Client error (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    
    async def solve_captcha(self, captcha_type: str, image_source: Union[str, Path, Image.Image], width: int = 348, height: int = 216, **kwargs) -> Dict[str, Any]:
        """
        Generic method to solve any supported TikTok captcha.
        
        Args:
            captcha_type: Type of captcha ('puzzle', 'whirl', '3d')
            image_source: URL, file path, or PIL Image of the captcha
            width: Width of the captcha image (default: 348)
            height: Height of the captcha image (default: 216)
            **kwargs: Additional parameters for specific captcha types (e.g., piece_url, url2)
            
        Returns:
            Dictionary containing the solution
        """
        if captcha_type not in self.VALID_CAPTCHA_TYPES:
            raise ValueError(f"Invalid captcha type: {captcha_type}. Must be one of {self.VALID_CAPTCHA_TYPES}")

        try:
            # Process image to base64
            image_base64 = await self._process_image(image_source)
            
            # Construct payload
            # The new API uses a single endpoint with 'cap_type' in the body
            # Keys depend on the captcha type based on error messages
            image_key = "image" # default
            
            if captcha_type == "3d":
                image_key = "image_base64"
            elif captcha_type == "puzzle":
                image_key = "puzzle_url" # Assuming URL for now, might need puzzle_base64 if using image
            elif captcha_type == "whirl":
                image_key = "url1" # Assuming URL
                
            payload = {
                image_key: image_base64,
                "cap_type": captcha_type,
                **kwargs
            }
            
            # Add specific parameters if needed
            if width and height:
                payload["width"] = width
                payload["height"] = height

            # Make request to the single endpoint
            url = f"{self.api_url}/tiktok/captcha"
            
            logger.info(f"Solving {captcha_type} captcha at endpoint: {url}")
            response_data = await self._make_api_request(url, payload)
            
            return response_data

        except Exception as e:
            logger.error(f"Failed to solve {captcha_type} captcha: {str(e)}")
            raise
    
    async def solve_slide(self, image_source: Union[str, Path, Image.Image], width: int = 348, height: int = 216, **kwargs) -> Dict[str, Any]:
        """
        Solve a Slide (Puzzle) captcha.
        
        Args:
            image_source: URL, file path, or PIL Image of the captcha (Background)
            width: Width of the captcha image (default: 348)
            height: Height of the captcha image (default: 216)
            **kwargs: Additional params like 'piece_url'
            
        Returns:
            Dictionary containing the solution (e.g., {'x': 123, 'y': 45})
        """
        # The new API calls this "puzzle"
        return await self.solve_captcha("puzzle", image_source, width, height, **kwargs)

    async def solve_whirl(self, image_source: Union[str, Path, Image.Image], width: int = 348, height: int = 216, **kwargs) -> Dict[str, Any]:
        """
        Solve a Whirl (Rotate) captcha.
        
        Args:
            image_source: URL, file path, or PIL Image of the captcha (Inner image)
            width: Width of the captcha image (default: 348)
            height: Height of the captcha image (default: 216)
            **kwargs: Additional params like 'url2' (Outer image)
            
        Returns:
            Dictionary containing the solution (e.g., {'angle': 45})
        """
        return await self.solve_captcha("whirl", image_source, width, height, **kwargs)

    async def solve_3d(self, image_source: Union[str, Path, Image.Image], width: int = 348, height: int = 216, **kwargs) -> Dict[str, Any]:
        """
        Solve a 3D (Two same objects) captcha.
        
        Args:
            image_source: URL, file path, or PIL Image of the captcha
            width: Width of the captcha image (default: 348)
            height: Height of the captcha image (default: 216)
            **kwargs: Additional params
            
        Returns:
            Dictionary containing the solution (e.g., {'objects': [1, 2]})
        """
        return await self.solve_captcha("3d", image_source, width, height, **kwargs)


# Convenience function for quick testing
async def test_solver():
    """Test the captcha solver with a sample image URL."""
    solver = TikTokCaptchaSolver()
    
    # Example 3D captcha URL from the API documentation
    test_url = "https://p19-rc-captcha-va.ibyteimg.com/tos-maliva-i-b4yrtqhy5a-us/3d_2385_8c09f6e7854724719b59d73732791824b8e49385_1.jpg~tplv-b4yrtqhy5a-3.webp"
    
    try:
        result = await solver.solve_3d(test_url, width=348, height=216)
        logger.info(f"Test result: {result}")
        return result
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run test
    asyncio.run(test_solver())
