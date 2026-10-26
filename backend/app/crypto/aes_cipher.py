"""
AES-256-CBC Cipher Module

Implements AES (Advanced Encryption Standard) with:
- 256-bit key length (the strongest standard AES variant)
- CBC (Cipher Block Chaining) operation mode
- PKCS7 padding
- Random IV (Initialization Vector) per encryption
- Encrypt-then-MAC with HMAC-SHA256 for integrity

=== WHY AES-256-CBC? ===

AES is the gold standard for symmetric encryption, adopted by NIST in 2001.
It replaced DES and has withstood over two decades of cryptanalysis.

WHY CBC MODE (not ECB):
- ECB (Electronic Codebook) encrypts each 16-byte block independently.
  This means identical plaintext blocks produce identical ciphertext blocks,
  which leaks patterns in the data. The famous "ECB Penguin" demonstrates
  how an image encrypted with ECB still shows the original shape.
- CBC (Cipher Block Chaining) XORs each plaintext block with the previous
  ciphertext block before encryption. This means identical plaintext blocks
  produce DIFFERENT ciphertext blocks, hiding all patterns.
- The first block has no "previous ciphertext" so we use an IV instead.

WHY PKCS7 PADDING:
- AES operates on fixed 16-byte (128-bit) blocks.
- If plaintext length is not a multiple of 16, we must pad it.
- PKCS7 appends N bytes each with value N (where N = bytes needed).
  Example: if 3 bytes of padding needed, append [0x03, 0x03, 0x03].
- If plaintext IS a multiple of 16, a FULL 16-byte padding block is added
  (16 bytes of 0x10) to avoid ambiguity during unpadding.
- This is unambiguous: read the last byte to know how many padding bytes to remove.

WHY RANDOM IV:
- The IV MUST be unpredictable for CBC mode to be secure.
- Reusing an IV with the same key allows attackers to detect if two
  messages start with the same plaintext blocks.
- We use os.urandom() which is cryptographically secure.
- The IV does NOT need to be secret - only unpredictable.
- We prepend it to the ciphertext so the decryptor can extract it.

CIPHERTEXT FORMAT:
    [16-byte IV][encrypted data with PKCS7 padding][32-byte HMAC-SHA256]

WHY ENCRYPT-THEN-MAC:
- We compute HMAC-SHA256 over (IV + ciphertext) AFTER encryption.
- During decryption, we verify the HMAC BEFORE decrypting.
- This prevents "padding oracle attacks" where an attacker manipulates
  ciphertext and uses error messages to gradually decrypt data.
- This follows the "Cryptographic Doom Principle" by Moxie Marlinspike.
"""
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import HMAC, SHA256

# AES block size is always 16 bytes (128 bits), regardless of key size
BLOCK_SIZE = AES.block_size  # 16 bytes
HMAC_SIZE = 32  # SHA256 produces 32-byte digest


def encrypt(plaintext: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Encrypt plaintext using AES-256-CBC with PKCS7 padding and HMAC integrity.
    
    Args:
        plaintext: The data to encrypt (arbitrary length)
        key: 32-byte AES-256 encryption key
        hmac_key: 32-byte key for HMAC-SHA256 integrity check
    
    Returns:
        bytes: [16-byte IV][padded ciphertext][32-byte HMAC]
    """
    # Generate a cryptographically random 16-byte IV
    # os.urandom() uses the OS's CSPRNG (e.g., /dev/urandom on Linux,
    # CryptGenRandom on Windows)
    iv = os.urandom(BLOCK_SIZE)
    
    # Create AES cipher in CBC mode with the random IV
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    
    # Pad plaintext to a multiple of 16 bytes using PKCS7
    padded_plaintext = pad(plaintext, BLOCK_SIZE, style='pkcs7')
    
    # Encrypt the padded plaintext
    ciphertext = cipher.encrypt(padded_plaintext)
    
    # Combine IV and ciphertext
    iv_and_ciphertext = iv + ciphertext
    
    # Compute HMAC-SHA256 over (IV + ciphertext) for integrity
    # This is the "Encrypt-then-MAC" pattern
    h = HMAC.new(hmac_key, iv_and_ciphertext, digestmod=SHA256)
    mac = h.digest()
    
    # Final format: [IV][ciphertext][HMAC]
    return iv_and_ciphertext + mac


def decrypt(data: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Decrypt AES-256-CBC encrypted data with HMAC verification.
    
    Args:
        data: The encrypted blob [IV][ciphertext][HMAC]
        key: 32-byte AES-256 encryption key
        hmac_key: 32-byte key for HMAC-SHA256 verification
    
    Returns:
        bytes: The original plaintext
    
    Raises:
        ValueError: If HMAC verification fails (data tampered)
        ValueError: If padding is invalid (wrong key or corrupted data)
    """
    # Validate minimum length: IV (16) + at least 1 block (16) + HMAC (32) = 64
    if len(data) < BLOCK_SIZE + BLOCK_SIZE + HMAC_SIZE:
        raise ValueError("Encrypted data is too short to be valid AES-CBC ciphertext")
    
    # Split the data: [IV + ciphertext] and [HMAC]
    iv_and_ciphertext = data[:-HMAC_SIZE]
    received_mac = data[-HMAC_SIZE:]
    
    # CRITICAL: Verify HMAC BEFORE decryption to prevent padding oracle attacks
    h = HMAC.new(hmac_key, iv_and_ciphertext, digestmod=SHA256)
    try:
        h.verify(received_mac)
    except ValueError:
        raise ValueError("HMAC verification failed: data has been tampered with")
    
    # Extract IV (first 16 bytes) and ciphertext (remaining)
    iv = iv_and_ciphertext[:BLOCK_SIZE]
    ciphertext = iv_and_ciphertext[BLOCK_SIZE:]
    
    # Create AES cipher with the extracted IV
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    
    # Decrypt and remove PKCS7 padding
    padded_plaintext = cipher.decrypt(ciphertext)
    plaintext = unpad(padded_plaintext, BLOCK_SIZE, style='pkcs7')
    
    return plaintext
