"""
Redirect endpoint for the URL shortener service.
Handles cache lookup, database fallback, and analytics tracking.
"""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from redis import asyncio as aioredis

from app.core.dependencies import get_redis_client, get_kafka_producer, get_session_for_shard
from app.core.config import settings, SHARD_DB_URL_LIST
from app.services.db_ops import get_url_by_short_code
from app.services.analytics import track_click_async
from app.core.request_id import generate_request_id
from app.services.hashing import shard_from_short_code
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{short_code}", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def redirect_to_url(
    request: Request,
    short_code: str,
    redis_client: aioredis.Redis = Depends(get_redis_client),
    kafka_producer = Depends(get_kafka_producer),
):
    """
    Redirects a short URL to the original URL.
    
    This endpoint:
    1. Checks Redis cache for the URL
    2. If not in cache, falls back to the database
    3. Updates analytics
    4. Returns a 302 redirect to the original URL
    
    Args:
        request: The incoming request
        short_code: The short code to redirect
        db: Database session
        redis_client: Redis client for caching
        
    Returns:
        RedirectResponse to the original URL
        
    Raises:
        HTTPException: 404 if the URL is not found
    """
    # Generate a request ID for tracking
    request_id = generate_request_id()
    
    # 1. CHECK CACHE:
    cache_key = f"url:{short_code}"
    long_url = await redis_client.get(cache_key)

    if long_url:
        # 2. IF CACHE HIT: Track the click and redirect
        logger.info(f"Cache hit for {short_code}, request_id={request_id}")
        
        # Track the click asynchronously (fire-and-forget) if Kafka is available
        if kafka_producer is not None:
            asyncio.create_task(
                track_click_async(
                    producer=kafka_producer,
                    short_code=short_code,
                    request_headers=dict(request.headers),
                    request_id=request_id,
                )
            )
        
        # Return the redirect
        return RedirectResponse(
            url=long_url,
            status_code=status.HTTP_302_FOUND,
            headers={"X-Request-ID": request_id}
        )
        
    # 3. IF CACHE MISS: Try the database
    logger.info(f"Cache miss for {short_code}, checking database, request_id={request_id}")
    
    # Determine primary shard and attempt lookup; if not found, fall back to other shards
    primary_shard = shard_from_short_code(short_code)
    shard_order = list(range(len(SHARD_DB_URL_LIST)))
    # Rotate so primary shard is first
    shard_order = shard_order[primary_shard:] + shard_order[:primary_shard]

    last_exception: Optional[Exception] = None
    for idx in shard_order:
        db: Session = get_session_for_shard(idx)
        try:
            long_url, request_count = await get_url_by_short_code(db, short_code)
            # Cache and analytics
            await redis_client.set(cache_key, long_url, ex=settings.REDIS_CACHE_TTL)
            if kafka_producer is not None:
                asyncio.create_task(
                    track_click_async(
                        producer=kafka_producer,
                        short_code=short_code,
                        request_headers=dict(request.headers),
                        request_id=request_id,
                    )
                )
            return RedirectResponse(
                url=long_url,
                status_code=status.HTTP_302_FOUND,
                headers={"X-Request-ID": request_id}
            )
        except HTTPException as e:
            # Only continue fallback on 404; re-raise others
            if e.status_code != status.HTTP_404_NOT_FOUND:
                last_exception = e
                break
            # else try next shard
        except Exception as e:
            last_exception = e
            break
        finally:
            db.close()

    # If we encountered a non-404 exception, surface it as 500
    if last_exception and not isinstance(last_exception, HTTPException):
        logger.error(f"Error redirecting {short_code}: {str(last_exception)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")

    # After checking all shards, return 404
    logger.warning(f"Short URL not found across shards: {short_code}, request_id={request_id}")
    raise HTTPException(status_code=404, detail=f"Short URL not found: {short_code}")