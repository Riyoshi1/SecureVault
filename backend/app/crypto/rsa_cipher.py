"""
RSA-2048 + OAEP (SHA-256) — Asymmetric primitives for Assignment 2 (Key Management)

References:
- Stallings, "Cryptography and Network Security" 7th Ed., Ch. 9.1
  (Principles of Public-Key Cryptosystems): encrypt with the RECIPIENT's public
  key so that only the holder of the matching private key can decrypt.
- Stallings Ch. 10.1 (Symmetric Key Distribution Using Asymmetric Encryption):
  public-key crypto is used to distribute a secret (session) key, while the bulk
  data is protected with fast symmetric ciphers (AES).
- OWASP Key Management Cheat Sheet: RSA >= 2048 bits, OAEP padding (never
  textbook RSA / PKCS#1 v1.5 for new designs), private keys never at rest in
  plaintext.

WHY OAEP?
- Textbook RSA is deterministic and malleable. OAEP adds randomness (same key
  encrypted twice -> different ciphertexts) and an integrity check on decryption,
  so a tampered ciphertext is REJECTED instead of silently producing garbage.

Private key at rest:
    The PEM private key is wrapped with the owner's AES-256-CBC key + HMAC-SHA256
    (Encrypt-then-MAC, see aes_cipher.py) derived from their Master Key
    (PBKDF2 -> HKDF). Only the plaintext public key is stored.
"""
import base64
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256

from app.crypto import aes_cipher

RSA_KEY_BITS = 2048


class RSADecryptionError(ValueError):
    """Raised when RSA-OAEP decryption fails (wrong key / tampered ciphertext)."""


def generate_keypair(bits: int = RSA_KEY_BITS) -> tuple[str, str]:
    """Generate an RSA key pair. Returns (public_pem, private_pem)."""
    key = RSA.generate(bits)
    private_pem = key.export_key(format="PEM").decode("utf-8")
    public_pem = key.publickey().export_key(format="PEM").decode("utf-8")
    return public_pem, private_pem


def wrap_private_key(private_pem: str, aes_key: bytes, hmac_key: bytes) -> bytes:
    """Encrypt (wrap) the PEM private key with AES-256-CBC + HMAC-SHA256."""
    return aes_cipher.encrypt(private_pem.encode("utf-8"), aes_key, hmac_key)


def unwrap_private_key(wrapped: bytes, aes_key: bytes, hmac_key: bytes) -> str:
    """Decrypt the wrapped PEM private key (raises ValueError on tamper/wrong key)."""
    return aes_cipher.decrypt(wrapped, aes_key, hmac_key).decode("utf-8")


def encrypt_with_public_key(plaintext: bytes, public_pem: str) -> bytes:
    """RSA-OAEP(SHA-256) encryption with the recipient's public key."""
    pub = RSA.import_key(public_pem)
    return PKCS1_OAEP.new(pub, hashAlgo=SHA256).encrypt(plaintext)


def decrypt_with_private_key(ciphertext: bytes, private_pem: str) -> bytes:
    """RSA-OAEP(SHA-256) decryption with the recipient's private key."""
    priv = RSA.import_key(private_pem)
    try:
        return PKCS1_OAEP.new(priv, hashAlgo=SHA256).decrypt(ciphertext)
    except (ValueError, TypeError) as e:
        raise RSADecryptionError(
            "RSA-OAEP Decryption Failed: Invalid Key or Corrupted Ciphertext"
        ) from e


def encrypt_key_b64(sym_key: bytes, public_pem: str) -> str:
    """Encrypt a symmetric key for distribution and return a Base64 'Encrypted Key Token'."""
    return base64.b64encode(encrypt_with_public_key(sym_key, public_pem)).decode("ascii")


def decrypt_key_b64(token_b64: str, private_pem: str) -> bytes:
    """Decode a Base64 Encrypted Key Token and RSA-OAEP decrypt it."""
    cleaned = "".join((token_b64 or "").split())  # tolerate line breaks from WA/Email
    try:
        ct = base64.b64decode(cleaned, validate=True)
    except Exception as e:
        raise RSADecryptionError(
            "RSA-OAEP Decryption Failed: Invalid Key or Corrupted Ciphertext (bad Base64)"
        ) from e
    if len(ct) != RSA_KEY_BITS // 8:
        raise RSADecryptionError(
            "RSA-OAEP Decryption Failed: Invalid Key or Corrupted Ciphertext "
            f"(expected {RSA_KEY_BITS // 8} bytes, got {len(ct)})"
        )
    return decrypt_with_private_key(ct, private_pem)


def public_key_fingerprint(public_pem: str) -> str:
    """SHA-256 fingerprint of the DER-encoded public key (colon-separated, first 16 bytes)."""
    der = RSA.import_key(public_pem).export_key(format="DER")
    h = hashlib.sha256(der).hexdigest()[:32]
    return ":".join(h[i:i + 2] for i in range(0, len(h), 2)).upper()
