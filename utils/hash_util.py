import hashlib

def hash_filename(filename: str) -> str:
    return hashlib.sha256(filename.encode()).hexdigest()
