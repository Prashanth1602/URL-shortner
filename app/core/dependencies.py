"""
Dependency injection setup for the URL shortener application.
"""
from typing import Generator, Optional
from contextlib import contextmanager

import aioredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pika import BlockingConnection, URLParameters
from pika.adapters.blocking_connection import BlockingChannel

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

# RabbitMQ setup
_rabbitmq_connection = None

def get_rabbitmq_channel() -> BlockingChannel:
    """
    Dependency that provides a RabbitMQ channel.
    This creates a single connection and reuses it for all requests.
    """
    global _rabbitmq_connection
    if _rabbitmq_connection is None or _rabbitmq_connection.is_closed:
        _rabbitmq_connection = BlockingConnection(URLParameters(settings.RABBITMQ_URL))
    
    channel = _rabbitmq_connection.channel()
    # Declare the exchange and queue for analytics
    channel.exchange_declare(exchange='analytics', exchange_type='direct')
    channel.queue_declare(queue='click_events', durable=True)
    channel.queue_bind(exchange='analytics', queue='click_events', routing_key='click')
    
    return channel

@contextmanager
def get_rabbitmq_channel_context() -> Generator[BlockingChannel, None, None]:
    """Context manager for RabbitMQ channel that ensures proper cleanup."""
    channel = None
    try:
        channel = get_rabbitmq_channel()
        yield channel
    finally:
        if channel and not channel.connection.is_closed:
            channel.close()
