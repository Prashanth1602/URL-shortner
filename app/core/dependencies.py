"""
Dependency injection and connection utilities for the URL shortener application.
Includes:
- Shard-aware SQLAlchemy session management (PostgreSQL)
- Redis client (aioredis)
- Kafka producer (aiokafka)
"""
from typing import Generator, Optional, List

from redis import asyncio as aioredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from aiokafka import AIOKafkaProducer
import logging

from app.core.config import settings, SHARD_DB_URL_LIST
from app.services.hashing import shard_from_url, shard_from_short_code

# -----------------------------
# Database: Shard-aware sessions
# -----------------------------
SHARD_ENGINES: List = []
SHARD_SESSIONS: List[sessionmaker] = []

def _init_shard_engines_once():
    global SHARD_ENGINES, SHARD_SESSIONS
    if SHARD_ENGINES:
        return
    for url in SHARD_DB_URL_LIST:
        engine = create_engine(url, pool_pre_ping=True)
        SHARD_ENGINES.append(engine)
        SHARD_SESSIONS.append(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_session_for_shard(shard_index: int) -> Session:
    """Get a SQLAlchemy session for a specific shard index."""
    _init_shard_engines_once()
    idx = shard_index % len(SHARD_SESSIONS)
    return SHARD_SESSIONS[idx]()

def get_db() -> Generator[Session, None, None]:
    """Default DB session (shard 0). Maintained for compatibility."""
    db = get_session_for_shard(0)
    try:
        yield db
    finally:
        db.close()

def get_db_by_url(url: str) -> Generator[Session, None, None]:
    """Provide a DB session for the shard derived from the URL."""
    shard_index = shard_from_url(url, settings.NUM_SHARDS)
    db = get_session_for_shard(shard_index)
    try:
        yield db
    finally:
        db.close()

def get_db_by_short_code(short_code: str) -> Generator[Session, None, None]:
    """Provide a DB session for the shard derived from the short code."""
    shard_index = shard_from_short_code(short_code, settings.NUM_SHARDS)
    db = get_session_for_shard(shard_index)
    try:
        yield db
    finally:
        db.close()

# ---------
# Redis
# ---------
_redis_pool: Optional[aioredis.Redis] = None

async def get_redis_client() -> aioredis.Redis:
    """Dependency that provides a Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool

# ---------
# Kafka
# ---------
_kafka_producer: Optional[AIOKafkaProducer] = None

async def get_kafka_producer() -> Optional[AIOKafkaProducer]:
    """Provide a shared AIOKafkaProducer instance; returns None if Kafka is unavailable."""
    global _kafka_producer
    # Return None immediately if Kafka is disabled
    if not settings.KAFKA_ENABLED:
        return None
    if _kafka_producer is None:
        try:
            producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
            await producer.start()
            _kafka_producer = producer
        except Exception as e:
            logging.getLogger(__name__).warning(f"Kafka unavailable: {e}")
            _kafka_producer = None
    return _kafka_producer

async def close_kafka_producer():
    global _kafka_producer
    if _kafka_producer is not None:
        try:
            await _kafka_producer.stop()
        finally:
            _kafka_producer = None
