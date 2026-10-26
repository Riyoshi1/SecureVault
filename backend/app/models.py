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
