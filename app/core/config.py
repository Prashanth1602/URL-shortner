"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "URL Shortener"
    DEBUG: bool = False
    
    # Database settings (PostgreSQL shards)
    # Comma-separated list of shard URLs (parsed post-load)
    SHARD_DB_URLS: str = ""
    NUM_SHARDS: int = 1
    # Compatibility: default DATABASE_URL (first shard)
    DATABASE_URL: Optional[str] = None
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 60 * 60 * 24 * 7  # 1 week in seconds
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_ENABLED: bool = False
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
parsed_shard_urls: List[str] = []
if settings.SHARD_DB_URLS:
    parsed_shard_urls = [s.strip() for s in settings.SHARD_DB_URLS.split(",") if s.strip()]
if parsed_shard_urls:
    if not settings.DATABASE_URL:
        settings.DATABASE_URL = parsed_shard_urls[0]
    if not settings.NUM_SHARDS or settings.NUM_SHARDS < 1:
        settings.NUM_SHARDS = len(parsed_shard_urls)
    # Attach back as list for general availability
    settings.SHARD_DB_URLS = ",".join(parsed_shard_urls)
    SHARD_DB_URL_LIST = parsed_shard_urls
else:
    # Fallback to single local SQLite if shards not configured (dev mode)
    settings.DATABASE_URL = settings.DATABASE_URL or "sqlite:///./test.db"
    parsed_shard_urls = [settings.DATABASE_URL]
    settings.NUM_SHARDS = 1

# Export a helper list for dependencies module
try:
    SHARD_DB_URL_LIST
except NameError:
    SHARD_DB_URL_LIST = parsed_shard_urls
