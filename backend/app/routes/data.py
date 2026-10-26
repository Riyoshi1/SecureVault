"""
Private Data Management Route Module

Provides endpoints to update and retrieve encrypted private personal data (PII).
All PII is encrypted with AES-CBC to ensure a high level of confidentiality and security.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import PrivateData
from app.schemas import PrivateDataUpdate, PrivateDataResponse
from app.routes.auth import get_current_user
from app.crypto.engine import CryptoEngine

router = APIRouter(prefix="/api/data", tags=["data"])

@router.put("/private", response_model=PrivateDataResponse)
async def update_private_data(
    data_update: PrivateDataUpdate,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update or insert private PII fields for the current user.
    
    Each field provided is individually encrypted using AES-CBC before storage.
    AES-CBC is chosen for PII data to provide strong, block-based encryption 
    suitable for sensitive information like Full Name, NIK, etc.
    """
    user, _, keys_dict = current_user
    
    # Fetch existing data for this user
    result = await db.execute(select(PrivateData).where(PrivateData.user_id == user.id))
    existing_data_records = result.scalars().all()
    existing_data_dict = {record.field_name: record for record in existing_data_records}
    
    updated_fields = {}
    
    # Update fields that are not None
    update_dict = data_update.model_dump(exclude_unset=True) if hasattr(data_update, 'model_dump') else data_update.dict(exclude_unset=True)
    
    for field_name, value in update_dict.items():
        if value is None:
            continue
            
        # PII data is always encrypted with AES-CBC as per requirements
        algorithm = "AES-CBC"
        try:
            # Encrypt the UTF-8 encoded string value
            encrypted_value = CryptoEngine.encrypt(value.encode('utf-8'), algorithm, keys_dict)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Encryption failed for {field_name}: {str(e)}")
            
        if field_name in existing_data_dict:
            # Update existing field
            existing_record = existing_data_dict[field_name]
            existing_record.encrypted_value = encrypted_value
            existing_record.algorithm = algorithm
        else:
            # Insert new field
            new_record = PrivateData(
                id=str(uuid.uuid4()),
                user_id=user.id,
                field_name=field_name,
                encrypted_value=encrypted_value,
                algorithm=algorithm
            )
            db.add(new_record)
            existing_data_dict[field_name] = new_record
            
        updated_fields[field_name] = value

    await db.commit()
    
    # Prepare the response containing decrypted values
    return PrivateDataResponse(**updated_fields)


@router.get("/private", response_model=PrivateDataResponse)
async def get_private_data(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve and decrypt all private PII fields for the current user.
    
    Reads encrypted records from the database and decrypts them on the fly 
    using the user's derived keys, ensuring data is only exposed in memory.
    """
    user, _, keys_dict = current_user
    
    result = await db.execute(select(PrivateData).where(PrivateData.user_id == user.id))
    records = result.scalars().all()
    
    decrypted_data = {}
    
    for record in records:
        try:
            # Decrypt the value using the algorithm specified in the record
            decrypted_bytes = CryptoEngine.decrypt(record.encrypted_value, record.algorithm, keys_dict)
            decrypted_data[record.field_name] = decrypted_bytes.decode('utf-8')
        except Exception as e:
            # If decryption fails (e.g., wrong key or corrupted data), we might want to skip or log
            decrypted_data[record.field_name] = "ERROR_DECRYPTING"
            
    return PrivateDataResponse(**decrypted_data)
