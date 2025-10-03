"""
Database operations for the URL shortener service.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.url_model import UrlMapping
from app.services.hashing import generate_short_code_and_shard_key
from typing import Optional, Tuple
from fastapi import HTTPException, status

# ... assume other imports and the create_or_get_short_code function definition ...

async def get_url_by_short_code(db: Session, short_code: str) -> Tuple[str, int]:
    """
    Retrieve the original URL and increment the request count for a short code.
    
    Args:
        db: Database session
        short_code: The short code to look up
        
    Returns:
        Tuple of (original_url, new_request_count)
        
    Raises:
        HTTPException: 404 if the short code is not found
    """
    # Find the URL mapping
    stmt = select(UrlMapping).where(UrlMapping.short_code == short_code)
    url_mapping = db.scalar(stmt)
    
    if not url_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL not found: {short_code}"
        )
    
    # Increment the request count
    url_mapping.request_count += 1
    db.commit()
    
    return str(url_mapping.original_link), url_mapping.request_count

async def create_or_get_short_code(
    db: Session, 
    original_link: str, 
    custom_code: Optional[str] = None
) -> str:
    """
    Checks if a URL already exists, validates custom codes, otherwise creates a new mapping.
    """
    
    # --- 1. CUSTOM CODE COLLISION CHECK (HIGH PRIORITY) ---
    if custom_code:
        # Check if this custom code is already in use by ANY URL
        stmt = select(UrlMapping.short_code).where(UrlMapping.short_code == custom_code)
        
        # db.scalar returns the value of the first column (the short_code) or None
        if db.scalar(stmt): 
            # If the code exists, raise the conflict error
            raise HTTPException(
                status_code=409, 
                detail=f"The custom short code '{custom_code}' is already in use."
            )
        
        # If the code is available, we use it instead of generating one
        final_code = custom_code
    
    # --- 2. DETERMINISTIC GENERATION & SHARD KEY ---
    else:
        # If no custom code, generate the deterministic one and the shard index
        generated_code, shard_index = generate_short_code_and_shard_key(original_link)
        final_code = generated_code

    # --- 3. URL REUSE CHECK (Deterministic Hash/Link Check) ---
    # Check if the original_link already exists on this shard (satisfies "do not waste storage")
    stmt = select(UrlMapping).where(UrlMapping.original_link == original_link)
    existing_mapping = db.scalar(stmt)
    
    if existing_mapping:
        # If found, reuse the existing short code.
        return existing_mapping.short_code

    # --- 4. CREATE NEW MAPPING & COMMIT ---
    new_mapping = UrlMapping(
        short_code=final_code, 
        original_link=original_link,
        request_count=0
    )

    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    
    return new_mapping.short_code