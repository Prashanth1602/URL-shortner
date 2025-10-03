"""
Dependency injection setup for the URL shortener application.
"""
from typing import Generator, Optional

import aioredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from aiokafka import AIOKafkaProducer

from app.core.config import settings

# Database setup
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis setup
_redis_pool: Optional[aioredis.Redis] = None

async def get_redis_client() -> aioredis.Redis:
    """Dependency that provides a Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool

# Kafka Producer setup (singleton)
_kafka_producer: Optional[AIOKafkaProducer] = None

async def get_kafka_producer() -> AIOKafkaProducer:
    """Provide a shared AIOKafkaProducer instance (started on first use)."""
    global _kafka_producer
    if _kafka_producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        _kafka_producer = producer
    return _kafka_producer

async def close_kafka_producer():
    global _kafka_producer
    if _kafka_producer is not None:
        try:
            await _kafka_producer.stop()
        finally:
            _kafka_producer = None
