import re
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime

# Auth
class UserRegister(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", v):
            raise ValueError("Username 3-30 karakter: huruf, angka, atau underscore")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password maksimal 72 byte (sekitar 72 karakter)")
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Password harus mengandung huruf dan angka")
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    created_at: datetime

# Private Data
class PrivateDataUpdate(BaseModel):
    full_name: Optional[str] = None
    nik: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        if v is None:
            return v
        v = " ".join(v.split())  # rapikan spasi ganda / spasi tepi
        if v and not re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*", v):
            raise ValueError("Nama lengkap hanya boleh berisi huruf dan spasi")
        return v

    @field_validator("nik")
    @classmethod
    def validate_nik(cls, v):
        if v is None:
            return v
        v = v.strip()
        if v and not re.fullmatch(r"\d{16}", v):
            raise ValueError("NIK harus tepat 16 digit angka")
        return v

class PrivateDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    full_name: Optional[str] = None
    nik: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None

# Files
class FileUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    file_category: str
    mime_type: str
    algorithm: str
    original_size: int
    created_at: datetime

class FileListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    files: List[FileUploadResponse]

# Benchmark
class BenchmarkRequest(BaseModel):
    data_size_kb: int = 100
    iterations: int = 10

class BenchmarkResultItem(BaseModel):
    algorithm: str
    encrypt_avg_ms: float
    decrypt_avg_ms: float
    encrypt_total_ms: float
    decrypt_total_ms: float
    data_size_bytes: int
    iterations: int
    ciphertext_size_bytes: int

class BenchmarkResponse(BaseModel):
    results: List[BenchmarkResultItem]

class CipherInspectRequest(BaseModel):
    plaintext: str = "Rahasia Negara - Kuliah Keamanan Informasi 2026"

class CipherInspectItem(BaseModel):
    algorithm: str
    mode: str
    block_size_bits: int
    key_size_bits: int
    plaintext_size_bytes: int
    total_output_bytes: int
    iv_or_nonce_hex: str
    iv_or_nonce_bytes: int
    ciphertext_hex: str
    ciphertext_bytes: int
    padding_bytes: int
    hmac_hex: str
    hmac_bytes: int
    encrypt_time_ms: float
    decrypt_time_ms: float

class CipherInspectResponse(BaseModel):
    plaintext: str
    plaintext_hex: str
    items: List[CipherInspectItem]
