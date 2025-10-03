from pydantic import BaseModel, HttpUrl
from typing import Optional

# Model for the Write Path (POST /shorten) request body
class ShortenRequest(BaseModel):
    # Enforces that the original_link is a valid URL
    original_link: HttpUrl
    
    # Allows user to specify a custom short code
    custom_short_code: Optional[str] = None

# Model for the API response (returns the created short code)
class ShortenResponse(BaseModel):
    short_code: str