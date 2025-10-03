from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

# Base is typically defined in a core DB file and imported
Base = declarative_base() 

class UrlMapping(Base):
    __tablename__ = 'url_mappings'

    # PK for fast lookups on sharded tables. Max 10 chars is safe for Base62(7-8 chars)
    short_code = Column(String(10), primary_key=True, index=True) 

    # We store the validated HttpUrl as a string.
    original_link = Column(String(2048), nullable=False) 

    # Counter for analytics and cache prioritization.
    request_count = Column(Integer, default=0, nullable=False)