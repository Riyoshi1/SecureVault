"""
Key Management & Sharing Route Module (Assignment 2)

Flow (Stallings Ch 10.1 "Symmetric Key Distribution Using Asymmetric Encryption"):

  1. Requester A  -> POST /api/sharing/request            (asks owner B for access)
  2. Owner B      -> POST /api/sharing/approve/{id}
        a. DEK  = 32 random bytes (Shared Symmetric Key / session key)
        b. B's PII + files are decrypted with B's own keys and re-encrypted
           with AES-256-CBC + HMAC-SHA256 under keys expanded from DEK (HKDF)
        c. DEK is WRAPPED with B's KEK (HKDF(master key)) and stored in
           `stored_symmetric_keys` — the raw DEK never touches the database
        d. token = Base64( RSA-OAEP-SHA256( A.public_key, DEK ) )
  3. B sends `token` to A "by other means" (WhatsApp / Email / .key file)
  4. Requester A  -> POST /api/sharing/access-shared-data
        A's private key is unwrapped with A's session master key, used to
        RSA-OAEP-decrypt the token -> DEK -> decrypt B's PII snapshot & files.
"""
import os
import json
import uuid
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select

from app.database import get_db
from app.config import settings
from app.models import User, PrivateData, UploadedFile, AccessRequest, StoredSymmetricKey, SharedFile
from app.schemas import (
    AccessRequestCreate, SharedAccessRequest, AccessRequestItem,
    SharedFileItem, SharedDataResponse, PrivateDataResponse,
)
from app.routes.auth import get_current_user, ensure_rsa_keys
from app.crypto import aes_cipher, rsa_cipher
from app.crypto.engine import CryptoEngine
from app.utils.security import derive_kek, derive_shared_dek_keys, key_fingerprint

router = APIRouter(prefix="/api/sharing", tags=["sharing"])

PII_FIELDS = ("full_name", "nik", "date_of_birth", "address")


def _shared_dir(request_id: str) -> str:
    return os.path.join(settings.ENCRYPTED_FILES_DIR, "shared", request_id)


async def _usernames(db, ids) -> dict:
    ids = list(set(ids))
    if not ids:
        return {}
    res = await db.execute(select(User).where(User.id.in_(ids)))
    return {u.id: u.username for u in res.scalars().all()}


async def _to_items(db, reqs) -> list[AccessRequestItem]:
    names = await _usernames(db, [r.requester_id for r in reqs] + [r.owner_id for r in reqs])
    return [
        AccessRequestItem(
            id=r.id, requester_id=r.requester_id, requester_username=names.get(r.requester_id, "?"),
            owner_id=r.owner_id, owner_username=names.get(r.owner_id, "?"), reason=r.reason,
            status=r.status, key_fingerprint=r.key_fingerprint,
            rsa_encrypted_key_b64=r.rsa_encrypted_key_b64,
            created_at=r.created_at, approved_at=r.approved_at,
        )
        for r in reqs
    ]


async def _get_request(db, request_id: str) -> AccessRequest:
    res = await db.execute(select(AccessRequest).where(AccessRequest.id == request_id))
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")
    return req


# ---------------------------------------------------------------------------
# Section A — My Cryptographic Key Vault
# ---------------------------------------------------------------------------
@router.get("/my-keys")
async def my_keys(current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, keys_dict = current_user
    await ensure_rsa_keys(user, keys_dict, db)  # covers sessions issued before the upgrade

    res = await db.execute(
        select(StoredSymmetricKey).where(StoredSymmetricKey.owner_id == user.id)
        .order_by(StoredSymmetricKey.created_at.desc())
    )
    stored = res.scalars().all()
    req_ids = [s.access_request_id for s in stored if s.access_request_id]
    reqs = {}
    if req_ids:
        r = await db.execute(select(AccessRequest).where(AccessRequest.id.in_(req_ids)))
        reqs = {x.id: x for x in r.scalars().all()}
    names = await _usernames(db, [x.requester_id for x in reqs.values()])

    return {
        "username": user.username,
        "rsa_key_bits": rsa_cipher.RSA_KEY_BITS,
        "rsa_padding": "OAEP (SHA-256, MGF1-SHA256)",
        "rsa_public_key": user.rsa_public_key,
        "rsa_public_key_fingerprint": rsa_cipher.public_key_fingerprint(user.rsa_public_key),
        "rsa_private_key_encrypted_hex": user.rsa_private_key_encrypted.hex(),
        "rsa_private_key_encrypted_bytes": len(user.rsa_private_key_encrypted),
        "rsa_private_key_wrap": "AES-256-CBC + HMAC-SHA256 (key = HKDF(PBKDF2(password)))",
        "wrapped_keys": [
            {
                "id": s.id,
                "purpose": s.purpose,
                "algorithm": s.algorithm,
                "wrap_algorithm": s.wrap_algorithm,
                "wrapped_key_hex": s.wrapped_key.hex(),
                "wrapped_key_bytes": len(s.wrapped_key),
                "key_fingerprint": s.key_fingerprint,
                "access_request_id": s.access_request_id,
                "shared_with": names.get(reqs[s.access_request_id].requester_id)
                if s.access_request_id in reqs else None,
                "created_at": s.created_at,
            }
            for s in stored
        ],
    }


# ---------------------------------------------------------------------------
# Section B — Directory & Request Access
# ---------------------------------------------------------------------------
@router.get("/users")
async def list_users(current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, _ = current_user
    res = await db.execute(select(User).where(User.id != user.id).order_by(User.username))
    return [
        {"id": u.id, "username": u.username, "has_rsa_key": bool(u.rsa_public_key), "created_at": u.created_at}
        for u in res.scalars().all()
    ]


@router.post("/request", response_model=AccessRequestItem)
async def create_request(body: AccessRequestCreate, current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, keys_dict = current_user
    if body.owner_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot request access to your own data")
    res = await db.execute(select(User).where(User.id == body.owner_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target user not found")

    res = await db.execute(select(AccessRequest).where(
        AccessRequest.requester_id == user.id, AccessRequest.owner_id == body.owner_id,
        AccessRequest.status == "PENDING"))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have a pending request to this user")

    # The requester must own an RSA key pair so the owner can encrypt the DEK for them
    await ensure_rsa_keys(user, keys_dict, db)

    req = AccessRequest(id=str(uuid.uuid4()), requester_id=user.id, owner_id=body.owner_id,
                        reason=body.reason, status="PENDING")
    db.add(req)
    await db.commit()
    return (await _to_items(db, [req]))[0]


# ---------------------------------------------------------------------------
# Section C / D — Incoming & Outgoing
# ---------------------------------------------------------------------------
@router.get("/incoming", response_model=list[AccessRequestItem])
async def incoming(current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, _ = current_user
    res = await db.execute(select(AccessRequest).where(AccessRequest.owner_id == user.id)
                           .order_by(AccessRequest.created_at.desc()))
    return await _to_items(db, res.scalars().all())


@router.get("/outgoing", response_model=list[AccessRequestItem])
async def outgoing(current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, _ = current_user
    res = await db.execute(select(AccessRequest).where(AccessRequest.requester_id == user.id)
                           .order_by(AccessRequest.created_at.desc()))
    items = await _to_items(db, res.scalars().all())
    # The requester receives the token ONLY out-of-band (WA/Email) — hide it here.
    for it in items:
        it.rsa_encrypted_key_b64 = None
    return items


@router.post("/approve/{request_id}")
async def approve(request_id: str, current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    owner, master_key, owner_keys = current_user
    req = await _get_request(db, request_id)
    if req.owner_id != owner.id:
        raise HTTPException(status_code=403, detail="Only the data owner can approve this request")
    if req.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}")

    res = await db.execute(select(User).where(User.id == req.requester_id))
    requester = res.scalar_one_or_none()
    if not requester or not requester.rsa_public_key:
        raise HTTPException(status_code=409, detail="Requester has no RSA public key yet (they must log in once)")

    # (a) Generate the Shared Symmetric Key (256-bit DEK) with the OS CSPRNG
    dek = os.urandom(32)
    shared = derive_shared_dek_keys(dek)
    fp = key_fingerprint(dek)

    # (b1) PII snapshot: decrypt with owner's keys, re-encrypt with the DEK
    res = await db.execute(select(PrivateData).where(PrivateData.user_id == owner.id))
    pii = {}
    for rec in res.scalars().all():
        try:
            pii[rec.field_name] = CryptoEngine.decrypt(rec.encrypted_value, rec.algorithm, owner_keys).decode("utf-8")
        except Exception:
            pii[rec.field_name] = None
    snapshot = aes_cipher.encrypt(json.dumps(pii).encode("utf-8"), shared["aes_key"], shared["hmac_key"])

    # (b2) Files: decrypt (AES/DES/RC4) with owner's keys, re-encrypt with AES-256-CBC under the DEK
    res = await db.execute(select(UploadedFile).where(UploadedFile.user_id == owner.id))
    out_dir = _shared_dir(req.id)
    os.makedirs(out_dir, exist_ok=True)
    shared_count = 0
    for f in res.scalars().all():
        if not os.path.exists(f.encrypted_file_path):
            continue
        with open(f.encrypted_file_path, "rb") as fh:
            plain = CryptoEngine.decrypt(fh.read(), f.algorithm, owner_keys)
        sid = str(uuid.uuid4())
        path = os.path.join(out_dir, f"{sid}.enc")
        with open(path, "wb") as fh:
            fh.write(aes_cipher.encrypt(plain, shared["aes_key"], shared["hmac_key"]))
        db.add(SharedFile(id=sid, access_request_id=req.id, source_file_id=f.id,
                          original_filename=f.original_filename, file_category=f.file_category,
                          mime_type=f.mime_type, source_algorithm=f.algorithm,
                          encrypted_file_path=path, original_size=f.original_size))
        shared_count += 1

    # (c) Envelope encryption: store the DEK only WRAPPED by the owner's KEK
    kek = derive_kek(master_key)
    wrapped = aes_cipher.encrypt(dek, kek["aes_key"], kek["hmac_key"])
    db.add(StoredSymmetricKey(id=str(uuid.uuid4()), owner_id=owner.id, access_request_id=req.id,
                              purpose=f"SHARED_DEK for {requester.username}", wrapped_key=wrapped,
                              key_fingerprint=fp))

    # (d) Key distribution: RSA-OAEP(requester public key, DEK) -> Base64 token
    token = rsa_cipher.encrypt_key_b64(dek, requester.rsa_public_key)
    del dek

    req.status = "APPROVED"
    req.approved_at = datetime.utcnow()
    req.encrypted_pii_snapshot = snapshot
    req.rsa_encrypted_key_b64 = token
    req.key_fingerprint = fp
    await db.commit()

    return {
        "request": (await _to_items(db, [req]))[0],
        "rsa_encrypted_key_b64": token,
        "wrapped_key_hex": wrapped.hex(),
        "key_fingerprint": fp,
        "requester_public_key_fingerprint": rsa_cipher.public_key_fingerprint(requester.rsa_public_key),
        "shared_pii_fields": [k for k, v in pii.items() if v],
        "shared_file_count": shared_count,
    }


@router.post("/deny/{request_id}", response_model=AccessRequestItem)
async def deny(request_id: str, current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    user, _, _ = current_user
    req = await _get_request(db, request_id)
    if req.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the data owner can deny this request")
    if req.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}")
    req.status = "DENIED"
    await db.commit()
    return (await _to_items(db, [req]))[0]


@router.post("/revoke/{request_id}", response_model=AccessRequestItem)
async def revoke(request_id: str, current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    """Crypto-shred: delete the shared ciphertexts and the wrapped DEK."""
    user, _, _ = current_user
    req = await _get_request(db, request_id)
    if req.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the data owner can revoke this request")
    if req.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only approved requests can be revoked")
    for model in (SharedFile, StoredSymmetricKey):
        res = await db.execute(select(model).where(model.access_request_id == req.id))
        for row in res.scalars().all():
            await db.delete(row)
    shutil.rmtree(_shared_dir(req.id), ignore_errors=True)
    req.status = "REVOKED"
    req.encrypted_pii_snapshot = None
    req.rsa_encrypted_key_b64 = None
    await db.commit()
    return (await _to_items(db, [req]))[0]


# ---------------------------------------------------------------------------
# Requester: unlock with the RSA-encrypted key received out-of-band
# ---------------------------------------------------------------------------
async def _unlock(body: SharedAccessRequest, current_user: tuple, db):
    user, _, keys_dict = current_user
    req = await _get_request(db, body.request_id)
    if req.requester_id != user.id:
        raise HTTPException(status_code=403, detail="This request does not belong to you")
    if req.status != "APPROVED":
        raise HTTPException(status_code=409, detail=f"Request is {req.status}, not APPROVED")
    if not user.rsa_private_key_encrypted:
        raise HTTPException(status_code=409, detail="You have no RSA key pair")

    # 1. Unwrap my RSA private key with my session Master-Key-derived AES key
    try:
        private_pem = rsa_cipher.unwrap_private_key(user.rsa_private_key_encrypted,
                                                    keys_dict["aes_key"], keys_dict["hmac_key"])
    except ValueError:
        raise HTTPException(status_code=500, detail="Could not unwrap your RSA private key")

    # 2. RSA-OAEP decrypt the pasted token -> Shared Symmetric Key
    try:
        dek = rsa_cipher.decrypt_key_b64(body.encrypted_key, private_pem)
    except rsa_cipher.RSADecryptionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if len(dek) != 32 or key_fingerprint(dek) != req.key_fingerprint:
        raise HTTPException(status_code=400,
                            detail="Key mismatch: this key was not issued for this access request")
    return req, derive_shared_dek_keys(dek)


@router.post("/access-shared-data", response_model=SharedDataResponse)
async def access_shared_data(body: SharedAccessRequest, current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    req, shared = await _unlock(body, current_user, db)
    try:
        pii = json.loads(aes_cipher.decrypt(req.encrypted_pii_snapshot, shared["aes_key"], shared["hmac_key"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"AES-256-CBC snapshot decryption failed: {e}")
    res = await db.execute(select(SharedFile).where(SharedFile.access_request_id == req.id))
    files = res.scalars().all()
    owner_name = (await _usernames(db, [req.owner_id])).get(req.owner_id, "?")
    return SharedDataResponse(
        request_id=req.id, owner_username=owner_name, key_fingerprint=req.key_fingerprint,
        pii=PrivateDataResponse(**{k: pii.get(k) for k in PII_FIELDS}),
        files=[SharedFileItem.model_validate(f) for f in files],
    )


@router.post("/shared-file/{file_id}")
async def download_shared_file(file_id: str, body: SharedAccessRequest,
                               current_user: tuple = Depends(get_current_user), db=Depends(get_db)):
    req, shared = await _unlock(body, current_user, db)
    res = await db.execute(select(SharedFile).where(SharedFile.id == file_id,
                                                    SharedFile.access_request_id == req.id))
    f = res.scalar_one_or_none()
    if not f or not os.path.exists(f.encrypted_file_path):
        raise HTTPException(status_code=404, detail="Shared file not found")
    with open(f.encrypted_file_path, "rb") as fh:
        try:
            plain = aes_cipher.decrypt(fh.read(), shared["aes_key"], shared["hmac_key"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"AES-256-CBC file decryption failed: {e}")
    safe_name = f.original_filename.replace('"', "")
    return StreamingResponse(iter([plain]), media_type=f.mime_type,
                             headers={"Content-Disposition": f'attachment; filename="{safe_name}"'})
