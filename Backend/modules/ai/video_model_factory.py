"""
Video model factory for easy model switching
"""
from typing import Optional
from loguru import logger

from .video_model_interface import VideoModelInterface
from .sora_model import SoraVideoModel
from .runway_model import RunwayVideoModel
from .pika_model import PikaVideoModel
from .luma_model import LumaVideoModel
from .kling_model import KlingVideoModel
from .hailuo_model import HailuoVideoModel


class VideoModelFactory:
    """Factory for creating video generation models"""
    
    @staticmethod
    def create_model(
        provider: str = "sora",
        model_variant: Optional[str] = None,
        **kwargs
    ) -> VideoModelInterface:
        """
        Create a video generation model
        
        Args:
            provider: "sora", "runway", "pika", etc.
            model_variant: Specific model variant (e.g., "sora-2-pro")
            **kwargs: Provider-specific configuration
            
        Returns:
            VideoModelInterface implementation
        """
        provider = provider.lower()
        
        if provider == "sora":
            model = model_variant or "sora-2"
            logger.info(f"Creating Sora model: {model}")
            return SoraVideoModel(model=model, **kwargs)
        
        elif provider == "runway":
            logger.info("Creating Runway Gen-3 Alpha Turbo model")
            return RunwayVideoModel(**kwargs)
        
        elif provider == "pika":
            logger.info("Creating Pika 1.5 model")
            return PikaVideoModel(**kwargs)
        
        elif provider == "luma":
            logger.info("Creating Luma Dream Machine model")
            return LumaVideoModel(**kwargs)
        
        elif provider == "kling":
            model = model_variant or "kling-2.1"
            logger.info(f"Creating Kling model: {model}")
            return KlingVideoModel(model=model, **kwargs)
        
        elif provider == "hailuo" or provider == "minimax":
            model = model_variant or "hailuo-02-pro"
            logger.info(f"Creating Hailuo model: {model}")
            return HailuoVideoModel(model=model, **kwargs)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available providers"""
        return ["sora", "runway", "pika", "luma", "kling", "hailuo"]
    
    @staticmethod
    def get_provider_models(provider: str) -> list:
        """Get available models for a provider"""
        models = {
            "sora": ["sora-2", "sora-2-pro"],
            "runway": ["gen3-alpha-turbo"],
            "pika": ["pika-1.5"],
            "luma": ["dream-machine"],
            "kling": ["kling-2.1", "kling-1.6"],
            "hailuo": ["hailuo-02", "hailuo-02-pro"],
        }
        return models.get(provider.lower(), [])


# Convenience function
def create_video_model(provider: str = "sora", **kwargs) -> VideoModelInterface:
    """
    Quick helper to create a video model
    
    Usage:
        model = create_video_model("sora", model_variant="sora-2-pro")
    """
    return VideoModelFactory.create_model(provider, **kwargs)


# Example usage
if __name__ == '__main__':
    # Create default Sora model
    model = create_video_model("sora")
    
    # Or create specific variant
    pro_model = create_video_model("sora", model_variant="sora-2-pro")
    
    print("Available providers:", VideoModelFactory.get_available_providers())
    print("Sora models:", VideoModelFactory.get_provider_models("sora"))
