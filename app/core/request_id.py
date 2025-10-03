"""
Utility for generating unique request IDs.
"""
import uuid

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())
