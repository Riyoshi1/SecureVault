"""
Authentication Route Module

Provides endpoints for user registration, login, and current user retrieval.
Implements secure authentication using JWT and password hashing, as well as 
cryptographic key derivation from the user's password for securing sensitive data.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.utils.security import (
    hash_password, verify_password, generate_salt, derive_master_key,
    derive_algorithm_keys, create_access_token, decode_access_token
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency to get the current authenticated user and their derived keys.
    
    This function extracts the JWT token, decodes it to retrieve the user ID and master key,
    and derives the algorithm-specific keys needed for encryption and decryption.
    """
    try:
        user_id, master_key = decode_access_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Derive algorithm-specific keys (AES, DES, RC4, HMAC) from the master key.
    # This ensures that specific algorithms have appropriate keys derived securely.
    keys_dict = derive_algorithm_keys(master_key)
    
    return user, master_key, keys_dict

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and return a JWT token so the user is logged in immediately.
    
    Generates a unique random salt for encryption purposes and hashes the user's password.
    The unique salt prevents rainbow table attacks on the derived keys.
    """
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
        
    encryption_salt = generate_salt()
    
    new_user = User(
        id=str(uuid.uuid4()),
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        encryption_salt=encryption_salt
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    master_key = derive_master_key(user_data.password, new_user.encryption_salt)
    access_token = create_access_token(new_user.id, master_key)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return a JWT token.
    
    Verifies the password, derives the master key using PBKDF2 (for resistance against brute force),
    and creates a JWT token that embeds the master key (encrypted/encoded securely via JWT_SECRET)
    so that subsequent requests can perform cryptographic operations.
    """
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Derive the master key using the user's password and unique salt.
    master_key = derive_master_key(user_data.password, user.encryption_salt)
    
    # Create the JWT access token carrying the user id and encrypted master key.
    # The master key is encrypted inside the JWT using Fernet (see security.py).
    access_token = create_access_token(user.id, master_key)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: tuple = Depends(get_current_user)):
    """
    Retrieve the current authenticated user's information.
    """
    user, _, _ = current_user
    return user
