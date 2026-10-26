"""
RC4 (ARC4) Stream Cipher Module

Implements RC4 (Rivest Cipher 4) with:
- 128-bit base key
- Per-message nonce-based key derivation (to prevent key reuse)
- Keystream drop of 3072 bytes (to mitigate known biases)
- HMAC-SHA256 for integrity

=== WHY RC4? ===

RC4 is a stream cipher designed by Ron Rivest in 1987. Unlike AES and DES
(block ciphers), RC4 generates a pseudorandom keystream that is XORed with
the plaintext byte-by-byte. This means:
- No padding is needed (no block size constraint)
- No operation mode is needed (no ECB/CBC/CTR)
- The ciphertext is the same length as the plaintext

IMPORTANT SECURITY NOTE:
RC4 is considered BROKEN for modern use:
- Known statistical biases in the keystream (Fluhrer-Mantin-Shamir attack, 2001)
- Exploited in practice against WEP and TLS (RFC 7465 prohibits RC4 in TLS)
- We include it for EDUCATIONAL comparison only.

WHY PER-MESSAGE NONCE KEY DERIVATION:
- RC4 is catastrophically vulnerable to key reuse. If the same key is used
  twice, XORing the two ciphertexts reveals the XOR of the two plaintexts,
  which is easily exploitable.
- To prevent this, we generate a random 16-byte nonce for each encryption
  and derive a unique per-message key: HMAC-SHA256(base_key, nonce)[:16]
- The nonce is prepended to the ciphertext for decryption.

WHY KEYSTREAM DROP (3072 bytes):
- The first ~256 bytes of RC4's keystream have known statistical biases.
- The Fluhrer-Mantin-Shamir (FMS) attack exploits correlations between
  the key and early keystream bytes.
- Dropping the first N bytes of keystream (N >= 768, we use 3072 for safety)
  mitigates these biases. This technique is called "RC4-drop[N]".
- 3072 bytes is a conservative choice recommended in academic literature.

CIPHERTEXT FORMAT:
    [16-byte nonce][ciphertext (same length as plaintext)][32-byte HMAC-SHA256]
"""
import os
from Crypto.Cipher import ARC4
from Crypto.Hash import HMAC, SHA256

NONCE_SIZE = 16
HMAC_SIZE = 32
KEYSTREAM_DROP = 3072  # Bytes to drop from initial keystream


def _derive_message_key(base_key: bytes, nonce: bytes) -> bytes:
    """
    Derive a unique per-message key from the base key and a random nonce.
    
    Uses HMAC-SHA256(base_key, nonce) truncated to 16 bytes.
    This ensures every encryption uses a different RC4 key,
    preventing the catastrophic key-reuse vulnerability.
    """
    h = HMAC.new(base_key, nonce, digestmod=SHA256)
    return h.digest()[:16]  # 128-bit per-message key


def encrypt(plaintext: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Encrypt plaintext using RC4 with per-message key derivation.
    
    Args:
        plaintext: The data to encrypt
        key: 16-byte RC4 base key
        hmac_key: 32-byte key for HMAC-SHA256
    
    Returns:
        bytes: [16-byte nonce][ciphertext][32-byte HMAC]
    """
    # Generate random nonce for per-message key derivation
    nonce = os.urandom(NONCE_SIZE)
    
    # Derive unique per-message key
    message_key = _derive_message_key(key, nonce)
    
    # Create RC4 cipher
    cipher = ARC4.new(message_key)
    
    # Drop first 3072 bytes of keystream to mitigate FMS attack biases
    # We "encrypt" dummy bytes and discard the output
    cipher.encrypt(b'\x00' * KEYSTREAM_DROP)
    
    # Encrypt the actual plaintext
    ciphertext = cipher.encrypt(plaintext)
    
    # Combine nonce and ciphertext
    nonce_and_ciphertext = nonce + ciphertext
    
    # Compute HMAC for integrity
    h = HMAC.new(hmac_key, nonce_and_ciphertext, digestmod=SHA256)
    mac = h.digest()
    
    return nonce_and_ciphertext + mac


def decrypt(data: bytes, key: bytes, hmac_key: bytes) -> bytes:
    """
    Decrypt RC4 encrypted data with HMAC verification.
    
    Args:
        data: Encrypted blob [nonce][ciphertext][HMAC]
        key: 16-byte RC4 base key
        hmac_key: 32-byte HMAC key
    
    Returns:
        bytes: Original plaintext
    
    Raises:
        ValueError: If HMAC verification fails
    """
    # Minimum: nonce (16) + at least 1 byte + HMAC (32) = 49
    if len(data) < NONCE_SIZE + 1 + HMAC_SIZE:
        raise ValueError("Encrypted data is too short to be valid RC4 ciphertext")
    
    # Split data
    nonce_and_ciphertext = data[:-HMAC_SIZE]
    received_mac = data[-HMAC_SIZE:]
    
    # Verify HMAC BEFORE decryption
    h = HMAC.new(hmac_key, nonce_and_ciphertext, digestmod=SHA256)
    try:
        h.verify(received_mac)
    except ValueError:
        raise ValueError("HMAC verification failed: data has been tampered with")
    
    # Extract nonce and ciphertext
    nonce = nonce_and_ciphertext[:NONCE_SIZE]
    ciphertext = nonce_and_ciphertext[NONCE_SIZE:]
    
    # Derive the same per-message key
    message_key = _derive_message_key(key, nonce)
    
    # Create RC4 cipher and drop keystream (same as encryption)
    cipher = ARC4.new(message_key)
    cipher.encrypt(b'\x00' * KEYSTREAM_DROP)
    
    # Decrypt
    plaintext = cipher.decrypt(ciphertext)
    
    return plaintext
