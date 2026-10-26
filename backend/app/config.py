from pydantic_settings import BaseSettings
import secrets

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./securevault.db"
    SERVER_SECRET: str = secrets.token_hex(32)
    JWT_SECRET: str = "default-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ENCRYPTED_FILES_DIR: str = "encrypted_files"
    PBKDF2_ITERATIONS: int = 600000

    class Config:
        env_file = ".env"

settings = Settings()
