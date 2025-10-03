# app/api/v1/endpoints/shorten.py (Completed)

from fastapi import APIRouter, status
from sqlalchemy.orm import Session
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services.db_ops import create_or_get_short_code
from app.core.dependencies import get_session_for_shard
from app.services.hashing import (
    shard_from_url,
    shard_from_short_code,
    generate_short_code_and_shard_key,
)

# Assume get_db is defined in your dependencies file
# NOTE: Using a placeholder router for simplicity
router = APIRouter() 

@router.post(
    "/shorten", 
    response_model=ShortenResponse, 
    status_code=status.HTTP_201_CREATED
)
async def shorten_url(
    request: ShortenRequest,
):
    """
    Main endpoint for creating a new short URL.
    """
    
    # 1. Extract the original_link and optional custom_code
    # Pydantic's HttpUrl needs to be converted back to a standard string for the database
    long_url = str(request.original_link) 
    custom_code = request.custom_short_code # This will be None if not provided
    
    # 2. Decide final code and target shard
    if custom_code:
        # If user supplied a custom code, route by that code deterministically
        target_shard = shard_from_short_code(custom_code)
        chosen_code = custom_code
    else:
        # Generate deterministic 8-char code and shard from the truncated code
        chosen_code, target_shard = generate_short_code_and_shard_key(long_url)

    # 3. Open session on target shard and persist
    db: Session = get_session_for_shard(target_shard)
    try:
        final_code = await create_or_get_short_code(
            db=db,
            original_link=long_url,
            custom_code=chosen_code,
        )
    finally:
        db.close()
    # 4. Return the response model containing the short code.
    return ShortenResponse(short_code=final_code)