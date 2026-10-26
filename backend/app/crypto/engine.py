"""
Crypto Engine - Unified Encryption Interface

Provides a single entry point for all encryption/decryption operations.
Routes to the appropriate cipher module based on the algorithm name.

This abstraction allows the rest of the application to be cipher-agnostic:
    CryptoEngine.encrypt(data, "AES-CBC", keys)
    CryptoEngine.decrypt(data, "AES-CBC", keys)

The engine handles key selection from the derived key dictionary.
"""
from app.crypto import aes_cipher, des_cipher, rc4_cipher

# Supported algorithms
ALGORITHMS = ["AES-CBC", "DES-CBC", "RC4"]

# Map algorithm names to their cipher modules
_CIPHER_MAP = {
    "AES-CBC": aes_cipher,
    "DES-CBC": des_cipher,
    "RC4": rc4_cipher,
}

# Map algorithm names to their key names in the derived key dictionary
_KEY_MAP = {
    "AES-CBC": "aes_key",
    "DES-CBC": "des_key",
    "RC4": "rc4_key",
}


class CryptoEngine:
    """
    Unified encryption engine supporting AES-CBC, DES-CBC, and RC4.
    
    Usage:
        keys = derive_algorithm_keys(master_key)
        encrypted = CryptoEngine.encrypt(plaintext, "AES-CBC", keys)
        decrypted = CryptoEngine.decrypt(encrypted, "AES-CBC", keys)
    """
    
    @staticmethod
    def encrypt(plaintext: bytes, algorithm: str, keys: dict) -> bytes:
        """
        Encrypt data using the specified algorithm.
        
        Args:
            plaintext: Raw bytes to encrypt
            algorithm: One of "AES-CBC", "DES-CBC", "RC4"
            keys: Dictionary from derive_algorithm_keys() containing
                  aes_key, des_key, rc4_key, and hmac_key
        
        Returns:
            Encrypted bytes (format depends on algorithm)
        
        Raises:
            ValueError: If algorithm is not supported
        """
        if algorithm not in _CIPHER_MAP:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Choose from: {', '.join(ALGORITHMS)}"
            )
        
        cipher_module = _CIPHER_MAP[algorithm]
        enc_key = keys[_KEY_MAP[algorithm]]
        hmac_key = keys["hmac_key"]
        
        return cipher_module.encrypt(plaintext, enc_key, hmac_key)
    
    @staticmethod
    def decrypt(data: bytes, algorithm: str, keys: dict) -> bytes:
        """
        Decrypt data using the specified algorithm.
        
        Args:
            data: Encrypted bytes
            algorithm: The algorithm used for encryption
            keys: Dictionary from derive_algorithm_keys()
        
        Returns:
            Decrypted plaintext bytes
        
        Raises:
            ValueError: If algorithm unsupported, HMAC fails, or decryption error
        """
        if algorithm not in _CIPHER_MAP:
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                f"Choose from: {', '.join(ALGORITHMS)}"
            )
        
        cipher_module = _CIPHER_MAP[algorithm]
        enc_key = keys[_KEY_MAP[algorithm]]
        hmac_key = keys["hmac_key"]
        
        return cipher_module.decrypt(data, enc_key, hmac_key)
    
    @staticmethod
    def get_algorithms() -> list[str]:
        """Return list of supported algorithm names."""
        return list(ALGORITHMS)
