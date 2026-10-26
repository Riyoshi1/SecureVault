"""
SecureVault - Main Application Entry Point

A secure data storage application demonstrating:
- AES-256-CBC encryption for sensitive PII data
- DES-CBC and RC4 encryption for file storage
- PBKDF2 + HKDF key derivation
- Encrypt-then-MAC integrity protection
- GDPR/UU PDP compliant encrypted data storage
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.config import settings
from app.routes import auth, data, files
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create encrypted files directory on startup
    os.makedirs(settings.ENCRYPTED_FILES_DIR, exist_ok=True)
    # Initialize database tables
    await init_db()
    yield

app = FastAPI(
    title="SecureVault API",
    description="Secure encrypted data storage with AES, DES, and RC4",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend (supports localhost and 127.0.0.1 on any port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
import logging

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Error handling {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server Error: {str(exc)}"},
    )

# Register route modules
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(files.router)

@app.get("/")
async def root():
    return {"message": "SecureVault API is running", "docs": "/docs"}

# Add benchmark route
from app.benchmark import run_benchmark, inspect_ciphers
from app.schemas import BenchmarkRequest, BenchmarkResponse, CipherInspectRequest, CipherInspectResponse
from fastapi import Body

@app.post("/api/benchmark/run", response_model=BenchmarkResponse)
async def benchmark_endpoint(req: BenchmarkRequest = Body(default=BenchmarkRequest())):
    results = run_benchmark(data_size_kb=req.data_size_kb, iterations=req.iterations)
    return BenchmarkResponse(results=results)

@app.post("/api/benchmark/inspect", response_model=CipherInspectResponse)
async def inspect_endpoint(req: CipherInspectRequest = Body(default=CipherInspectRequest())):
    return inspect_ciphers(req.plaintext)
