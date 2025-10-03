import hashlib
from app.core.config import settings

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

def base62_decode(encoded: str) -> int:
    """Converts a Base62 string back into a decimal integer."""
    value = 0
    for char in encoded:
        value = value * BASE + BASE62_ALPHABET.index(char)
    return value

def generate_short_code_and_shard_key(url: str, num_shards: int = None) -> tuple[str, int]:
    """
    Generates a truncated Base62 short code and calculates the shard index
    from the truncated code to ensure read/write consistency.
    """
    num = num_shards or settings.NUM_SHARDS

    # 1. Generate the Raw Hash ID (the large number)
    raw_id = generate_raw_hash(url)

    # 2. Generate the Short Code (Encoding Logic) and truncate to 8 chars
    full_code = base62_encode(raw_id)
    short_code = full_code[:8]

    # 3. Calculate the Shard Index from the truncated code (consistent mapping)
    shard_index = shard_from_short_code(short_code, num)

    # 4. Return (short_code, shard_index)
    return short_code, shard_index

def shard_from_short_code(short_code: str, num_shards: int = None) -> int:
    """Derive shard index from the truncated short_code by decoding and modulo shard count."""
    raw_part = base62_decode(short_code)
    num = num_shards or settings.NUM_SHARDS
    return raw_part % num

def shard_from_url(url: str, num_shards: int = None) -> int:
    raw_id = generate_raw_hash(url)
    num = num_shards or settings.NUM_SHARDS
    return raw_id % num