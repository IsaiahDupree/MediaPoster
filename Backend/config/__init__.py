"""
Configuration module for MediaPoster
Loads environment variables and provides application settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields from .env
        env_file='.env',
        case_sensitive=False
    )
    
    # API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    blotato_api_key: str = Field(default="", env="BLOTATO_API_KEY")
    google_drive_credentials_path: str = Field(
        default="credentials/google_drive.json",
        env="GOOGLE_DRIVE_CREDENTIALS_PATH"
    )
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_drive_folder_id: str = Field(..., env="GOOGLE_DRIVE_FOLDER_ID")
    
    # Expose uppercase for OpenAI client compatibility
    @property
    def OPENAI_API_KEY(self) -> str:
        return self.openai_api_key
    
    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_jwt_secret: Optional[str] = Field(None, env="SUPABASE_JWT_SECRET")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Social Media Account IDs
    instagram_account_id: Optional[str] = Field(None, env="INSTAGRAM_ACCOUNT_ID")
    tiktok_account_id: Optional[str] = Field(None, env="TIKTOK_ACCOUNT_ID")
    youtube_channel_id: Optional[str] = Field(None, env="YOUTUBE_CHANNEL_ID")
    twitter_account_id: Optional[str] = Field(None, env="TWITTER_ACCOUNT_ID")
    
    # Application Settings
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    max_video_size_mb: int = Field(default=5000, env="MAX_VIDEO_SIZE_MB")  # Supports large iPhone videos
    temp_dir: str = Field(default="/tmp/mediaposter", env="TEMP_DIR")
    working_dir: str = Field(default="./workspace", env="WORKING_DIR")
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    # Processing Settings
    max_concurrent_jobs: int = Field(default=3, env="MAX_CONCURRENT_JOBS")
    whisper_model: str = Field(default="medium", env="WHISPER_MODEL")
    gpt_model: str = Field(default="gpt-4-vision-preview", env="GPT_MODEL")
    frame_extraction_fps: int = Field(default=1, env="FRAME_EXTRACTION_FPS")
    
    # Platform Settings
    default_clip_duration: int = Field(default=45, env="DEFAULT_CLIP_DURATION")
    min_clip_duration: int = Field(default=15, env="MIN_CLIP_DURATION")
    max_clip_duration: int = Field(default=60, env="MAX_CLIP_DURATION")
    target_aspect_ratio: str = Field(default="9:16", env="TARGET_ASPECT_RATIO")
    
    # Performance Thresholds
    low_performance_views_threshold: int = Field(default=100, env="LOW_PERFORMANCE_VIEWS_THRESHOLD")
    low_performance_check_delay_minutes: int = Field(default=10, env="LOW_PERFORMANCE_CHECK_DELAY_MINUTES")
    delete_low_performers: bool = Field(default=True, env="DELETE_LOW_PERFORMERS")
    
    # Watermark Removal
    watermark_detection_threshold: float = Field(default=0.8, env="WATERMARK_DETECTION_THRESHOLD")
    use_ai_watermark_removal: bool = Field(default=True, env="USE_AI_WATERMARK_REMOVAL")


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        
        # Create necessary directories
        os.makedirs(_settings.temp_dir, exist_ok=True)
        os.makedirs(_settings.working_dir, exist_ok=True)
        
        # Ensure critical env vars are in os.environ for legacy code
        if _settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = _settings.openai_api_key
        if _settings.blotato_api_key:
            os.environ["BLOTATO_API_KEY"] = _settings.blotato_api_key
    
    return _settings


# Export settings instance
settings = get_settings()
