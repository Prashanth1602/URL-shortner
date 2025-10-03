"""
Application configuration settings.
"""
from pydantic import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "URL Shortener"
    DEBUG: bool = False
    
    # Database settings (PostgreSQL shards)
    # Comma-separated list of shard URLs
    SHARD_DB_URLS: List[str] = []
    NUM_SHARDS: int = 1
    # Compatibility: default DATABASE_URL (first shard)
    DATABASE_URL: Optional[str] = None
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 60 * 60 * 24 * 7  # 1 week in seconds
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_CLICK_EVENTS: str = "click_events"
    KAFKA_CONSUMER_GROUP: str = "analytics_consumer_group"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    
    # Number of shards for URL storage (used in hashing)
    # Defaults to length of SHARD_DB_URLS if provided
    # Overridden by env NUM_SHARDS if set explicitly
    # Note: keep consistent across services
    # value set in __post_init__-like logic below
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Normalize shard settings after load
if settings.SHARD_DB_URLS:
    # Ensure list type when loaded from env (comma-separated)
    if isinstance(settings.SHARD_DB_URLS, str):
        settings.SHARD_DB_URLS = [s.strip() for s in settings.SHARD_DB_URLS.split(",") if s.strip()]
    if not settings.DATABASE_URL:
        settings.DATABASE_URL = settings.SHARD_DB_URLS[0]
    # If NUM_SHARDS not explicitly set (>0), derive from list length
    if not settings.NUM_SHARDS or settings.NUM_SHARDS < 1:
        settings.NUM_SHARDS = len(settings.SHARD_DB_URLS)
else:
    # Fallback to single local SQLite if shards not configured (dev mode)
    settings.DATABASE_URL = settings.DATABASE_URL or "sqlite:///./test.db"
    settings.SHARD_DB_URLS = [settings.DATABASE_URL]
    settings.NUM_SHARDS = 1
