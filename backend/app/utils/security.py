"""
Security Utilities - Key Derivation, Password Hashing, JWT Management

This module handles the bridge between user authentication and encryption:
1. Password hashing (bcrypt) for authentication
2. Key derivation (PBKDF2 + HKDF) for encryption
3. JWT token creation with encrypted master key

KEY DESIGN DECISIONS:
- bcrypt is used for password verification (one-way hash, NOT for key derivation)
- PBKDF2-HMAC-SHA256 is used for deriving the encryption master key from the password
  because it produces a deterministic output (same password + salt = same key),
  which is needed to decrypt previously encrypted data.
- HKDF is used to derive separate keys for each algorithm from the master key.
  This follows the principle of key separation: compromising one key doesn't
  compromise the others.
- The master key is encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using
  SERVER_SECRET before embedding in JWT. This way, even if the JWT is stolen,
  the master key is protected by the server secret.
"""
import os
import base64
import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from Crypto.Protocol.KDF import PBKDF2, HKDF
from Crypto.Hash import SHA256, HMAC as CryptoHMAC
from app.config import settings

# Fernet cipher for encrypting master key inside JWT
# Fernet requires a 32-byte URL-safe base64-encoded key
# We derive it from SERVER_SECRET using SHA256
def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.SERVER_SECRET.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_salt() -> bytes:
    return os.urandom(16)

def derive_master_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte master key from user's password using PBKDF2-HMAC-SHA256.
    
    WHY PBKDF2?
    - Key derivation function designed to be computationally expensive to thwart brute-force.
    - 600,000 iterations is the OWASP 2024 recommendation for PBKDF2-HMAC-SHA256.
    - Uses hashlib.pbkdf2_hmac for C-level OpenSSL acceleration.
    - Deterministic: same password + salt produces the exact same key for decryption.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        settings.PBKDF2_ITERATIONS,
        dklen=32
    )

def derive_algorithm_keys(master_key: bytes) -> dict:
    """
    Derive separate keys for each encryption algorithm using HKDF.
    
    WHY HKDF (HMAC-based Key Derivation Function)?
    - Extracts entropy from the master key and expands it into multiple keys.
    - Using different 'context' values ensures each derived key is independent.
    - KEY SEPARATION PRINCIPLE: if one algorithm's key is compromised,
      the others remain secure.
    
    WHY SEPARATE HMAC KEY?
    - Used for Encrypt-then-MAC integrity verification.
    - Must be independent from encryption keys to maintain security properties.
    """
    aes_key = HKDF(
        master=master_key,
        key_len=32,      # AES-256 requires 32-byte key
        salt=b"",
        hashmod=SHA256,
        context=b"securevault-aes-256-cbc-key"
    )
    des_key = HKDF(
        master=master_key,
        key_len=8,       # DES requires 8-byte key (56 effective bits)
        salt=b"",
        hashmod=SHA256,
        context=b"securevault-des-cbc-key"
    )
    rc4_key = HKDF(
        master=master_key,
        key_len=16,      # RC4 with 128-bit key
        salt=b"",
        hashmod=SHA256,
        context=b"securevault-rc4-key"
    )
    hmac_key = HKDF(
        master=master_key,
        key_len=32,      # HMAC-SHA256 key
        salt=b"",
        hashmod=SHA256,
        context=b"securevault-hmac-key"
    )
    return {
        "aes_key": aes_key,
        "des_key": des_key,
        "rc4_key": rc4_key,
        "hmac_key": hmac_key,
    }

def create_access_token(user_id: str, master_key: bytes) -> str:
    """
    Create a JWT containing the user_id and an encrypted version of the master key.
    
    WHY ENCRYPT THE MASTER KEY IN THE JWT?
    - We need the master key on every request to decrypt data.
    - Storing it in plaintext in the JWT would be a security risk.
    - Encrypting it with Fernet (using SERVER_SECRET) ensures:
      1. Only this server can decrypt it.
      2. If the JWT is intercepted, the master key is still protected.
    - This keeps the server stateless (no server-side sessions needed).
    """
    fernet = _get_fernet()
    encrypted_mk = fernet.encrypt(master_key).decode('utf-8')
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "mk": encrypted_mk,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_access_token(token: str) -> tuple[str, bytes]:
    """
    Decode JWT and return (user_id, master_key).
    Raises JWTError or ValueError on failure.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        encrypted_mk = payload.get("mk")
        if not user_id or not encrypted_mk:
            raise ValueError("Invalid token payload")
        
        fernet = _get_fernet()
        master_key = fernet.decrypt(encrypted_mk.encode('utf-8'))
        return user_id, master_key
    except JWTError:
        raise ValueError("Invalid or expired token")
