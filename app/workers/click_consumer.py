"""
Kafka consumer worker that processes click events and updates request_count idempotently.
Run with: python -m app.workers.click_consumer
"""
import asyncio
import json
import logging
from typing import Optional

from aiokafka import AIOKafkaConsumer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import get_redis_client, get_session_for_shard
from app.services.hashing import shard_from_short_code
from models.url_model import UrlMapping

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def process_message(db: Session, redis, message: bytes):
    try:
        event = json.loads(message.decode("utf-8"))
        event_type = event.get("event_type")
        request_id = event.get("request_id")
        short_code = event.get("short_code")
        
        if event_type != "click" or not request_id or not short_code:
            logger.warning("Skipping invalid event: %s", event)
            return
        
        # Idempotency check via Redis key
        processed_key = f"click:processed:{request_id}"
        if await redis.get(processed_key):
            logger.info("Duplicate event ignored: %s", request_id)
            return
        
        # Increment request_count in DB
        stmt = select(UrlMapping).where(UrlMapping.short_code == short_code)
        mapping = db.scalar(stmt)
        if mapping:
            mapping.request_count = int(mapping.request_count) + 1
            db.commit()
        else:
            logger.warning("Short code not found in DB for click: %s", short_code)
        
        # Mark as processed in Redis with TTL to avoid indefinite growth
        await redis.set(processed_key, "1", ex=60 * 60 * 24 * 7)
    except Exception as e:
        logger.exception("Failed to process message: %s", e)

async def consume():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_CLICK_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    redis = await get_redis_client()

    try:
        logger.info("Kafka consumer started on topic: %s", settings.KAFKA_TOPIC_CLICK_EVENTS)
        async for msg in consumer:
            # Determine shard per short_code and open session
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                sc = payload.get("short_code")
            except Exception:
                sc = None
            if not sc:
                logger.warning("Message missing short_code; skipping")
                continue
            shard_index = shard_from_short_code(sc)
            db = get_session_for_shard(shard_index)
            try:
                await process_message(db, redis, msg.value)
            finally:
                db.close()
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())
