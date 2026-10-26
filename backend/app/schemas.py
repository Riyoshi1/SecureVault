from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# Auth
class UserRegister(BaseModel):
    username: str
    password: str

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
