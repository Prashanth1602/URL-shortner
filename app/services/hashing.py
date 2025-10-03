import hashlib
from typing import tuple

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(BASE62_ALPHABET) # 62

def generate_raw_hash(url: str) -> int:
    """Generates a large integer hash from the given URL using SHA-256."""
    
    # 1. Encode the URL to bytes
    url_bytes = url.encode("utf-8")
    
    # 2. Hash the bytes using SHA-256
    sha256_hash = hashlib.sha256(url_bytes)
    
    # 3. Convert the hexadecimal digest to an integer (using base 16)
    raw_id = int(sha256_hash.hexdigest(), 16)
    
    return raw_id

def base62_encode(decimal_id: int) -> str:
    """Converts a large decimal number (the raw hash) into a Base62 string."""
    
    if decimal_id == 0:
        return BASE62_ALPHABET[0] 
        
    encoded = ""
    
    while decimal_id > 0:
        # 1. Get the remainder (the index of the next character)
        remainder = decimal_id % BASE

        # 2. Prepend the character at that index to 'encoded'
        encoded = BASE62_ALPHABET[remainder] + encoded

        # 3. Update the number by integer division
        decimal_id //= BASE

    return encoded

def generate_short_code_and_shard_key(url: str, num_shards: int = 100) -> tuple[str, int]:
    """
    Generates the short code and calculates the shard index for storage.
    """
    
    # 1. Generate the Raw Hash ID (the large number)
    raw_id = generate_raw_hash(url)

    # 2. Calculate the Shard Index (Scaling Logic)
    shard_index = raw_id % num_shards

    # 3. Generate the Short Code (Encoding Logic)
    short_code = base62_encode(raw_id)
    
    # Note: We will truncate this code later (e.g., [:8]) to keep it short.

    # 4. Return (short_code, shard_index)
    return short_code, shard_index