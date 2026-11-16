import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, LargeBinary, ForeignKey
from sqlalchemy.dialects.sqlite import TEXT
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    encryption_salt = Column(LargeBinary(16), nullable=False)  # 16-byte salt for PBKDF2
    # --- Assignment 2: RSA-2048 key pair ---
    rsa_public_key = Column(TEXT, nullable=True)               # PEM, plaintext (public)
    rsa_private_key_encrypted = Column(LargeBinary, nullable=True)  # AES-256-CBC+HMAC wrapped PEM
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PrivateData(Base):
    __tablename__ = "private_data"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(50), nullable=False)  # e.g. full_name, nik, dob, address
    encrypted_value = Column(LargeBinary, nullable=False)
    algorithm = Column(String(20), default="AES-CBC")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_category = Column(String(20), nullable=False)  # image, document, video
    mime_type = Column(String(100), nullable=False)
    algorithm = Column(String(20), nullable=False)  # AES-CBC, DES-CBC, RC4
    encrypted_file_path = Column(String(500), nullable=False)
    original_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# =====================================================================
# Assignment 2 — Key Management (Stallings Ch 9.1 / 10.1, OWASP KM)
# =====================================================================

class AccessRequest(Base):
    """A request by `requester` to view the private data of `owner`."""
    __tablename__ = "access_requests"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(500), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING | APPROVED | DENIED | REVOKED
    # RSA-OAEP(requester public key) of the shared DEK, Base64. Safe to keep: only
    # the requester's private key can open it. Allows the owner to re-send it.
    rsa_encrypted_key_b64 = Column(TEXT, nullable=True)
    # PII snapshot encrypted with the Shared DEK (AES-256-CBC + HMAC-SHA256)
    encrypted_pii_snapshot = Column(LargeBinary, nullable=True)
    key_fingerprint = Column(String(64), nullable=True)  # SHA-256(DEK)[:16] hex — for UI verification
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)


class StoredSymmetricKey(Base):
    """
    Key Vault: Data Encryption Keys (DEKs) stored ONLY in wrapped form.
    wrapped_key = AES-256-CBC(KEK, DEK) || HMAC-SHA256  (KEK = HKDF(owner master key))
    """
    __tablename__ = "stored_symmetric_keys"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_request_id = Column(String(36), ForeignKey("access_requests.id", ondelete="CASCADE"), nullable=True)
    purpose = Column(String(100), default="SHARED_DEK")
    algorithm = Column(String(50), default="AES-256-CBC")
    wrap_algorithm = Column(String(100), default="AES-256-CBC + HMAC-SHA256 (KEK via HKDF)")
    wrapped_key = Column(LargeBinary, nullable=False)
    key_fingerprint = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SharedFile(Base):
    """A copy of an owner's file re-encrypted with the Shared DEK for one access request."""
    __tablename__ = "shared_files"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    access_request_id = Column(String(36), ForeignKey("access_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    source_file_id = Column(String(36), nullable=True)
    original_filename = Column(String(255), nullable=False)
    file_category = Column(String(20), nullable=False)
    mime_type = Column(String(100), nullable=False)
    source_algorithm = Column(String(20), nullable=False)
    encrypted_file_path = Column(String(500), nullable=False)
    original_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
