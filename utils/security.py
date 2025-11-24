"""
API key encryption and security utilities.
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


def get_cipher():
    """Get Fernet cipher from environment key."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in environment")
    return Fernet(key.encode())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key."""
    cipher = get_cipher()
    return cipher.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_key.encode()).decode()
