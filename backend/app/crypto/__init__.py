"""
Cryptography Module for SecureVault

This module implements three symmetric encryption algorithms:
- AES-256-CBC: Advanced Encryption Standard with 256-bit key in CBC mode
- DES-CBC: Data Encryption Standard in CBC mode  
- RC4 (ARC4): Rivest Cipher 4, a stream cipher

All cipher modules follow the same interface:
    encrypt(plaintext: bytes, key: bytes, hmac_key: bytes) -> bytes
    decrypt(data: bytes, key: bytes, hmac_key: bytes) -> bytes

The CryptoEngine class provides a unified interface for selecting algorithms.
"""
from app.crypto.engine import CryptoEngine

__all__ = ["CryptoEngine"]
