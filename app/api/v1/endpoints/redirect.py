"""
Redirect endpoint for the URL shortener service.
Handles cache lookup, database fallback, and analytics tracking.
"""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import aioredis

from app.core.dependencies import get_redis_client, get_kafka_producer, get_session_for_shard
from app.core.config import settings
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
        
        # Track the click asynchronously (fire-and-forget)
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
    
    # Determine shard and open session
    shard_index = shard_from_short_code(short_code)
    db: Session = get_session_for_shard(shard_index)
    try:
        # Get the URL from the database
        long_url, request_count = await get_url_by_short_code(db, short_code)
        
        # Update cache for future requests (with a TTL)
        await redis_client.set(
            cache_key,
            long_url,
            ex=settings.REDIS_CACHE_TTL
        )
        
        # Track the click asynchronously (fire-and-forget)
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
        
    except HTTPException as e:
        # Re-raise 404 errors
        if e.status_code == status.HTTP_404_NOT_FOUND:
            logger.warning(f"URL not found: {short_code}, request_id={request_id}")
            raise
        # Re-raise other HTTP exceptions
        raise
    except Exception as e:
        # Log other errors and return a 500
        logger.error(f"Error redirecting {short_code}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )
    finally:
        db.close()