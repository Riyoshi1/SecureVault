"""
DES-CBC Cipher Module

Implements DES (Data Encryption Standard) with:
- 64-bit key (56 effective bits; 8 bits are parity)
- CBC (Cipher Block Chaining) operation mode
- PKCS5 padding (equivalent to PKCS7 with 8-byte block size)
- Random IV per encryption
- Encrypt-then-MAC with HMAC-SHA256

=== WHY DES-CBC? ===

DES was the US federal encryption standard from 1977 to 2002.
It uses a 56-bit key and 64-bit (8-byte) block size.

IMPORTANT SECURITY NOTE:
DES is considered INSECURE for modern use due to its short 56-bit key,
which is vulnerable to brute-force attacks (demonstrated in 1999 by the
EFF's "Deep Crack" machine in under 24 hours). We include it here
for EDUCATIONAL PURPOSES to compare with AES and RC4.

In production, use AES-256 or AES-128 instead.

WHY CBC MODE (not ECB):
- Same reasoning as AES: ECB leaks patterns, CBC does not.
- DES-ECB is especially dangerous because the smaller 8-byte block size
  means repetitions are MORE likely than with AES's 16-byte blocks.

WHY PKCS5 PADDING:
- PKCS5 is functionally identical to PKCS7 for 8-byte blocks.
- DES operates on 8-byte blocks, so padding aligns data to 8 bytes.
- Same logic: append N bytes of value N.

CIPHERTEXT FORMAT:
    [8-byte IV][encrypted data with PKCS5 padding][32-byte HMAC-SHA256]

KEY PARITY:
- DES keys are 8 bytes, but only 56 bits are used for encryption.
- The least significant bit of each byte is a parity bit.
- We call DES.adjust_key_parity() to set these correctly.
"""
import os
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import HMAC, SHA256

# DES block size is 8 bytes (64 bits)
BLOCK_SIZE = DES.block_size  # 8 bytes
HMAC_SIZE = 32  # SHA256 digest
KEY_SIZE = DES.key_size  # 8 bytes


def adjust_key_parity(key: bytes) -> bytes:
    """
    Set the least significant bit (LSB) of each byte in the 8-byte DES key
    so that every byte has odd parity (an odd number of '1' bits).
    In the DES specification (FIPS 46-3), 56 bits are used for the Feistel
    subkeys and 8 bits (1 per byte) are used for odd parity checking.
    """
    adjusted = bytearray()
    for b in key:
        # Clear LSB, then set it to 1 if the number of 1-bits in upper 7 bits is even
        b_7bits = b & 0xFE
        ones_count = bin(b_7bits).count("1")
        parity_bit = 1 if (ones_count % 2 == 0) else 0
        adjusted.append(b_7bits | parity_bit)
    return bytes(adjusted)


def encrypt(plaintext: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Encrypt plaintext using DES-CBC with PKCS5 padding and HMAC integrity.
    
    Args:
        plaintext: The data to encrypt
        key: 8-byte DES key
        hmac_key: 32-byte key for HMAC-SHA256
    
    Returns:
        bytes: [8-byte IV][padded ciphertext][32-byte HMAC]
    """
    # Adjust key parity bits (DES requirement)
    # Each byte's LSB is set so that each byte has odd parity
    adjusted_key = adjust_key_parity(key)
    
    # Generate random 8-byte IV
    iv = os.urandom(BLOCK_SIZE)
    
    # Create DES cipher in CBC mode
    cipher = DES.new(adjusted_key, DES.MODE_CBC, iv=iv)
    
    # Pad plaintext to multiple of 8 bytes using PKCS5
    # (PyCryptodome's pkcs7 with block_size=8 is equivalent to PKCS5)
    padded_plaintext = pad(plaintext, BLOCK_SIZE, style='pkcs7')
    
    # Encrypt
    ciphertext = cipher.encrypt(padded_plaintext)
    
    # Combine IV and ciphertext
    iv_and_ciphertext = iv + ciphertext
    
    # Compute HMAC for integrity (Encrypt-then-MAC)
    h = HMAC.new(hmac_key, iv_and_ciphertext, digestmod=SHA256)
    mac = h.digest()
    
    return iv_and_ciphertext + mac


def decrypt(data: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Decrypt DES-CBC encrypted data with HMAC verification.
    
    Args:
        data: Encrypted blob [IV][ciphertext][HMAC]
        key: 8-byte DES key
        hmac_key: 32-byte HMAC key
    
    Returns:
        bytes: Original plaintext
    
    Raises:
        ValueError: If HMAC fails or padding is invalid
    """
    # Minimum: IV (8) + 1 block (8) + HMAC (32) = 48
    if len(data) < BLOCK_SIZE + BLOCK_SIZE + HMAC_SIZE:
        raise ValueError("Encrypted data is too short to be valid DES-CBC ciphertext")
    
    # Split data
    iv_and_ciphertext = data[:-HMAC_SIZE]
    received_mac = data[-HMAC_SIZE:]
    
    # Verify HMAC BEFORE decryption
    h = HMAC.new(hmac_key, iv_and_ciphertext, digestmod=SHA256)
    try:
        h.verify(received_mac)
    except ValueError:
        raise ValueError("HMAC verification failed: data has been tampered with")
    
    # Extract IV and ciphertext
    iv = iv_and_ciphertext[:BLOCK_SIZE]
    ciphertext = iv_and_ciphertext[BLOCK_SIZE:]
    
    # Adjust key parity and decrypt
    adjusted_key = adjust_key_parity(key)
    cipher = DES.new(adjusted_key, DES.MODE_CBC, iv=iv)
    
    padded_plaintext = cipher.decrypt(ciphertext)
    plaintext = unpad(padded_plaintext, BLOCK_SIZE, style='pkcs7')
    
    return plaintext
