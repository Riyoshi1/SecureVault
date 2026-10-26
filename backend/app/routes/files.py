"""
File Management Route Module

Provides endpoints for uploading, downloading, listing, and deleting user files.
Files are encrypted symmetrically with user-chosen algorithms (AES, DES, RC4) before storage on disk,
and the cryptographic metadata is stored in the database.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import UploadedFile
from app.schemas import FileUploadResponse, FileListResponse
from app.routes.auth import get_current_user
from app.config import settings
from app.crypto.engine import CryptoEngine, ALGORITHMS

router = APIRouter(prefix="/api/files", tags=["files"])

def get_file_category(mime_type: str) -> str:
    """Determine file category based on MIME type."""
    if mime_type in ["image/jpeg", "image/png"]:
        return "image"
    elif mime_type in [
        "application/pdf", "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]:
        return "document"
    elif mime_type in ["video/mp4", "video/avi", "video/quicktime", "video/x-matroska"]:
        return "video"
    else:
        return "other"

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    algorithm: str = Form(...),
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and encrypt a file.
    
    The file is fully read into memory (for simplicity and cryptography limits in this example),
    encrypted using the requested algorithm (AES, DES, RC4), and then written to disk.
    This demonstrates flexibility in choosing encryption schemes for different performance/security trade-offs.
    """
    user, _, keys_dict = current_user
    
    if algorithm not in ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Unsupported algorithm. Choose from: {', '.join(ALGORITHMS)}")
        
    file_bytes = await file.read()
    original_size = len(file_bytes)
    
    # Encrypt the file data
    try:
        encrypted_bytes = CryptoEngine.encrypt(file_bytes, algorithm, keys_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")
        
    # Prepare directory for user's encrypted files
    user_dir = os.path.join(settings.ENCRYPTED_FILES_DIR, user.id)
    os.makedirs(user_dir, exist_ok=True)
    
    file_uuid = str(uuid.uuid4())
    encrypted_file_path = os.path.join(user_dir, f"{file_uuid}.enc")
    
    # Write encrypted bytes to disk
    with open(encrypted_file_path, "wb") as f:
        f.write(encrypted_bytes)
        
    content_type = file.content_type or "application/octet-stream"
    file_category = get_file_category(content_type)
    
    new_file = UploadedFile(
        id=file_uuid,
        user_id=user.id,
        original_filename=file.filename or "uploaded_file",
        file_category=file_category,
        mime_type=content_type,
        algorithm=algorithm,
        encrypted_file_path=encrypted_file_path,
        original_size=original_size
    )
    
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    
    return FileUploadResponse.model_validate(new_file)

@router.get("/list", response_model=FileListResponse)
async def list_files(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all uploaded and encrypted files for the current user.
    """
    user, _, _ = current_user
    
    result = await db.execute(select(UploadedFile).where(UploadedFile.user_id == user.id))
    files = result.scalars().all()
    
    return FileListResponse(files=[FileUploadResponse.model_validate(f) for f in files])

@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download and decrypt a file.
    
    Reads the encrypted file from disk, decrypts it in memory using the specific 
    algorithm recorded during upload, and streams the plaintext back to the client.
    """
    user, _, keys_dict = current_user
    
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.user_id == user.id))
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or unauthorized")
        
    if not os.path.exists(file_record.encrypted_file_path):
        raise HTTPException(status_code=404, detail="Encrypted file missing on disk")
        
    with open(file_record.encrypted_file_path, "rb") as f:
        encrypted_bytes = f.read()
        
    try:
        decrypted_bytes = CryptoEngine.decrypt(encrypted_bytes, file_record.algorithm, keys_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {str(e)}")
        
    def iterfile():
        yield decrypted_bytes
        
    return StreamingResponse(
        iterfile(), 
        media_type=file_record.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_record.original_filename}"'}
    )

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user's encrypted file from both database and disk.
    """
    user, _, _ = current_user
    
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.user_id == user.id))
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or unauthorized")
        
    # Remove from disk
    if os.path.exists(file_record.encrypted_file_path):
        os.remove(file_record.encrypted_file_path)
        
    # Remove from DB
    await db.delete(file_record)
    await db.commit()
    
    return {"message": "File deleted successfully"}
