"""
Application configuration settings.
"""
from pydantic import BaseSettings, HttpUrl, AnyUrl
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "URL Shortener"
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./test.db"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 60 * 60 * 24 * 7  # 1 week in seconds
    
    # RabbitMQ settings
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    
    # Number of shards for URL storage
    NUM_SHARDS: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
