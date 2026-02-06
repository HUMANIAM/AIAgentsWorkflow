"""Secret code generator module."""
import hashlib


def hash_int(n):
    """Return SHA-256 hash of integer n as hex string."""
    # Convert integer to string, encode to bytes
    data = str(n).encode('utf-8')
    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(data)
    # Return hexadecimal representation
    return hash_obj.hexdigest()
