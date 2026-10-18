"""
Configuration module for MediaPoster
Loads environment variables and provides application settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
from pathlib import Path
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
    supabase_url: str = Field(default="http://127.0.0.1:54321", env="SUPABASE_URL")
    supabase_key: str = Field(default="", env="SUPABASE_KEY")
    supabase_jwt_secret: Optional[str] = Field(None, env="SUPABASE_JWT_SECRET")
    supabase_studio_url: str = Field(default="http://127.0.0.1:54323", env="SUPABASE_STUDIO_URL")
    supabase_inbucket_url: str = Field(default="http://127.0.0.1:54324", env="SUPABASE_INBUCKET_URL")
    supabase_db_port: int = Field(default=54322, env="SUPABASE_DB_PORT")
    
    # Database
    database_url: str = Field(default="postgresql://postgres:postgres@127.0.0.1:54322/postgres", env="DATABASE_URL")
    database_url_async: str = Field(default="postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres", env="DATABASE_URL_ASYNC")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # RapidAPI
    rapidapi_key: str = Field(default="", env="RAPIDAPI_KEY")
    
    # Social Media Account IDs (supports multiple comma-separated)
    instagram_account_id: Optional[str] = Field(None, env="INSTAGRAM_ACCOUNT_ID")
    instagram_usernames: str = Field(default="", env="INSTAGRAM_USERNAMES")
    tiktok_account_id: Optional[str] = Field(None, env="TIKTOK_ACCOUNT_ID")
    tiktok_usernames: str = Field(default="", env="TIKTOK_USERNAMES")
    youtube_channel_id: Optional[str] = Field(None, env="YOUTUBE_CHANNEL_ID")
    youtube_channel_ids: str = Field(default="", env="YOUTUBE_CHANNEL_IDS")
    twitter_account_id: Optional[str] = Field(None, env="TWITTER_ACCOUNT_ID")
    twitter_usernames: str = Field(default="", env="TWITTER_USERNAMES")
    linkedin_profile_urls: str = Field(default="", env="LINKEDIN_PROFILE_URLS")
    threads_usernames: str = Field(default="", env="THREADS_USERNAMES")
    pinterest_usernames: str = Field(default="", env="PINTEREST_USERNAMES")
    medium_usernames: str = Field(default="", env="MEDIUM_USERNAMES")
    
    # Server Configuration
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=5555, env="BACKEND_PORT")
    backend_url: str = Field(default="http://localhost:5555", env="BACKEND_URL")
    frontend_url: str = Field(default="http://localhost:5557", env="FRONTEND_URL")
    dashboard_url: str = Field(default="http://localhost:5557", env="DASHBOARD_URL")
    
    # Application Settings
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    max_video_size_mb: int = Field(default=5000, env="MAX_VIDEO_SIZE_MB")  # Supports large iPhone videos
    temp_dir: str = Field(default="/tmp/mediaposter", env="TEMP_DIR")
    working_dir: str = Field(default="./workspace", env="WORKING_DIR")

    # Worker Queue Configuration (MOD-003)
    use_redis_queue: bool = Field(
        default_factory=lambda: bool(os.getenv("REDIS_URL")),
        env="USE_REDIS_QUEUE"
    )
    queue_max_size: int = Field(default=1000, env="QUEUE_MAX_SIZE")
    queue_worker_concurrency: int = Field(default=5, env="QUEUE_WORKER_CONCURRENCY")
    queue_poll_interval: float = Field(default=1.0, env="QUEUE_POLL_INTERVAL")
    queue_max_retries: int = Field(default=3, env="QUEUE_MAX_RETRIES")
    queue_retry_delay: float = Field(default=5.0, env="QUEUE_RETRY_DELAY")

    # Media Factory Configuration
    media_factory_enabled: bool = Field(default=True, env="MEDIA_FACTORY_ENABLED")
    media_factory_output_dir: str = Field(default="./output/media_factory", env="MEDIA_FACTORY_OUTPUT_DIR")

    # TTS Configuration
    tts_provider: str = Field(default="huggingface", env="TTS_PROVIDER")  # huggingface, elevenlabs
    huggingface_api_key: Optional[str] = Field(None, env="HUGGINGFACE_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(None, env="ELEVENLABS_API_KEY")

    # Music Configuration
    music_provider: str = Field(default="suno", env="MUSIC_PROVIDER")  # suno, soundcloud
    suno_api_key: Optional[str] = Field(None, env="SUNO_API_KEY")

    # Remotion Configuration
    remotion_enabled: bool = Field(default=True, env="REMOTION_ENABLED")
    remotion_timeout: int = Field(default=300, env="REMOTION_TIMEOUT")  # 5 minutes

    # Sleep Mode Configuration
    sleep_mode_enabled: bool = Field(default=True, env="SLEEP_MODE_ENABLED")
    sleep_mode_grace_period: float = Field(default=2.0, env="SLEEP_MODE_GRACE_PERIOD")
    sleep_mode_check_interval: int = Field(default=30, env="SLEEP_MODE_CHECK_INTERVAL")
    
    # Video Source Directory - PRIMARY: iPhone Import (116GB, 8491 items)
    # Host path: ~/Documents/IphoneImport
    # Docker path: /media/IphoneImport (mounted in docker-compose.yml)
    video_source_dir: str = Field(
        default=str(Path.home() / "Documents" / "IphoneImport"),
        env="VIDEO_SOURCE_DIR"
    )
    watch_directories: Optional[str] = Field(
        default=None,
        env="WATCH_DIRECTORIES"
    )  # Comma-separated list of directories to watch
    
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
    """
    Get or create settings instance (MOD-004: Config Management)

    This implements centralized configuration management with:
    - Environment variable loading
    - Default values
    - Type validation via Pydantic
    - Automatic directory creation
    """
    global _settings
    if _settings is None:
        _settings = Settings()

        # Create necessary directories
        os.makedirs(_settings.temp_dir, exist_ok=True)
        os.makedirs(_settings.working_dir, exist_ok=True)
        os.makedirs(_settings.media_factory_output_dir, exist_ok=True)

        # Ensure critical env vars are in os.environ for legacy code
        if _settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = _settings.openai_api_key
        if _settings.blotato_api_key:
            os.environ["BLOTATO_API_KEY"] = _settings.blotato_api_key
        if _settings.rapidapi_key:
            os.environ["RAPIDAPI_KEY"] = _settings.rapidapi_key

    return _settings


def validate_config() -> dict[str, list[str]]:
    """
    Validate configuration and return missing required fields.

    Returns:
        Dictionary mapping service names to lists of missing config keys
    """
    settings = get_settings()
    missing = {}

    # Check OpenAI (required for most features)
    if not settings.openai_api_key:
        missing.setdefault("openai", []).append("OPENAI_API_KEY")

    # Check database
    if not settings.database_url:
        missing.setdefault("database", []).append("DATABASE_URL")

    # Check Blotato (required for publishing)
    if not settings.blotato_api_key:
        missing.setdefault("blotato", []).append("BLOTATO_API_KEY")

    # Check TTS providers
    if settings.tts_provider == "huggingface" and not settings.huggingface_api_key:
        missing.setdefault("tts", []).append("HUGGINGFACE_API_KEY")
    elif settings.tts_provider == "elevenlabs" and not settings.elevenlabs_api_key:
        missing.setdefault("tts", []).append("ELEVENLABS_API_KEY")

    return missing


def is_production() -> bool:
    """Check if running in production environment."""
    settings = get_settings()
    return settings.app_env.lower() in ("production", "prod")


def is_development() -> bool:
    """Check if running in development environment."""
    settings = get_settings()
    return settings.app_env.lower() in ("development", "dev")


# Export settings instance
settings = get_settings()


__all__ = [
    "Settings",
    "get_settings",
    "validate_config",
    "is_production",
    "is_development",
    "settings",
]
