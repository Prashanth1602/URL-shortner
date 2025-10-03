# app/api/v1/endpoints/shorten.py (Completed)

from fastapi import APIRouter, status
from sqlalchemy.orm import Session
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services.db_ops import create_or_get_short_code
from app.core.dependencies import get_session_for_shard
from app.services.hashing import shard_from_url

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
    
    # 2. Pick shard from URL and open a session
    shard_index = shard_from_url(long_url)
    db: Session = get_session_for_shard(shard_index)
    try:
        # 3. Call the core service function
        final_code = await create_or_get_short_code(
            db=db,
            original_link=long_url,
            custom_code=custom_code,
        )
    finally:
        db.close()
    # 4. Return the response model containing the short code.
    return ShortenResponse(short_code=final_code)