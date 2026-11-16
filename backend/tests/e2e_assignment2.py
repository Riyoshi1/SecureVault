"""
End-to-end verification for Assignment 2 (and Assignment 1 regression).

Run from backend/:   python tests/e2e_assignment2.py

Uses an isolated temporary SQLite DB that starts with the OLD Assignment-1
`users` schema to prove the graceful migration + RSA backfill on login.
"""
import os
import sys
import base64
import sqlite3
import tempfile

TMP = tempfile.mkdtemp(prefix="sv_a2_")
DB = os.path.join(TMP, "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB}"
os.environ["ENCRYPTED_FILES_DIR"] = os.path.join(TMP, "enc")
os.environ["SERVER_SECRET"] = "test-secret"
os.environ["JWT_SECRET"] = "test-jwt"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- Build an Assignment-1 style DB with a legacy user (no RSA columns) ----
from app.utils.security import hash_password, generate_salt  # noqa: E402
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, encryption_salt BLOB NOT NULL, created_at DATETIME, updated_at DATETIME)""")
con.execute("INSERT INTO users (id, username, password_hash, encryption_salt) VALUES (?,?,?,?)",
            ("legacy-0001", "legacy_bob", hash_password("Password123"), generate_salt()))
con.commit(); con.close()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

ok = lambda m: print(f"  [PASS] {m}")


def check(cond, msg):
    if not cond:
        print(f"  [FAIL] {msg}"); sys.exit(1)
    ok(msg)


with TestClient(app) as c:
    H = lambda t: {"Authorization": f"Bearer {t}"}
    print("== 1. Registration / backward-compatible login ==")
    ta = c.post("/api/auth/register", json={"username": "alice_hr", "password": "Alice12345"}).json()["access_token"]
    r = c.post("/api/auth/login", json={"username": "legacy_bob", "password": "Password123"})
    check(r.status_code == 200, "Legacy Assignment-1 user can log in after migration")
    tb = r.json()["access_token"]
    raw = sqlite3.connect(DB).execute(
        "SELECT rsa_public_key, rsa_private_key_encrypted FROM users WHERE username='legacy_bob'").fetchone()
    check(raw[0].startswith("-----BEGIN PUBLIC KEY-----"), "RSA public key auto-generated for legacy user")
    check(b"PRIVATE KEY" not in raw[1], "RSA private key stored ENCRYPTED (no PEM plaintext in DB)")

    print("== 2. Assignment-1 regression (owner Bob) ==")
    pii = {"full_name": "Bob Santoso", "nik": "3171234567890001", "date_of_birth": "1990-05-17", "address": "Jl. Merdeka 1"}
    check(c.put("/api/data/private", json=pii, headers=H(tb)).status_code == 200, "PII saved (AES-256-CBC)")
    check(c.get("/api/data/private", headers=H(tb)).json() == pii, "PII decrypts correctly")
    blobs = {
        "ktp.png": (b"\x89PNG\r\n\x1a\n" + os.urandom(3000), "image/png", "AES-CBC"),
        "cv.pdf": (b"%PDF-1.4\n" + os.urandom(5000), "application/pdf", "DES-CBC"),
        "intro.mp4": (os.urandom(20000), "video/mp4", "RC4"),
    }
    for name, (data, mime, alg) in blobs.items():
        r = c.post("/api/files/upload", files={"file": (name, data, mime)}, data={"algorithm": alg}, headers=H(tb))
        check(r.status_code == 200, f"Upload {name} with {alg}")
        fid = r.json()["id"]
        check(c.get(f"/api/files/download/{fid}", headers=H(tb)).content == data, f"Download {name} round-trip")
    check(c.post("/api/benchmark/inspect", json={"plaintext": "x"}).status_code == 200, "Hex inspector works")

    print("== 3. Alice requests Bob's data ==")
    users = c.get("/api/sharing/users", headers=H(ta)).json()
    bob_id = next(u["id"] for u in users if u["username"] == "legacy_bob")
    r = c.post("/api/sharing/request", json={"owner_id": bob_id, "reason": "HR Background Check"}, headers=H(ta))
    check(r.status_code == 200 and r.json()["status"] == "PENDING", "Access request created")
    req_id = r.json()["id"]
    check(c.post("/api/sharing/request", json={"owner_id": bob_id}, headers=H(ta)).status_code == 409, "Duplicate pending rejected")
    check(c.post(f"/api/sharing/approve/{req_id}", headers=H(ta)).status_code == 403, "Requester cannot self-approve")

    print("== 4. Bob approves -> DEK generated, wrapped, RSA-encrypted ==")
    r = c.post(f"/api/sharing/approve/{req_id}", headers=H(tb))
    check(r.status_code == 200, "Approve OK")
    ap = r.json()
    token = ap["rsa_encrypted_key_b64"]
    check(len(base64.b64decode(token)) == 256, "Token is 256-byte RSA-2048 OAEP ciphertext (Base64)")
    check(ap["shared_file_count"] == 3, "3 files re-encrypted under the Shared DEK")
    vault = c.get("/api/sharing/my-keys", headers=H(tb)).json()
    check(len(vault["wrapped_keys"]) == 1 and vault["wrapped_keys"][0]["wrapped_key_bytes"] == 96,
          "Wrapped DEK stored in Key Vault (16 IV + 48 ct[32B key + 16B PKCS7] + 32 HMAC = 96 bytes)")
    out = c.get("/api/sharing/outgoing", headers=H(ta)).json()
    check(out[0]["status"] == "APPROVED" and out[0]["rsa_encrypted_key_b64"] is None,
          "Requester sees APPROVED but token is NOT delivered in-band")

    print("== 5. Alice unlocks with the out-of-band token ==")
    body = {"request_id": req_id, "encrypted_key": token}
    r = c.post("/api/sharing/access-shared-data", json=body, headers=H(ta))
    check(r.status_code == 200, "RSA-OAEP decrypt + snapshot decrypt OK")
    sd = r.json()
    check(sd["pii"] == pii, "Bob's PII recovered exactly")
    for f in sd["files"]:
        d = c.post(f"/api/sharing/shared-file/{f['id']}", json=body, headers=H(ta)).content
        check(d == blobs[f["original_filename"]][0], f"Shared file {f['original_filename']} ({f['source_algorithm']}) recovered")

    print("== 6. Negative tests ==")
    ct = bytearray(base64.b64decode(token)); ct[100] ^= 0x01
    r = c.post("/api/sharing/access-shared-data", json={"request_id": req_id, "encrypted_key": base64.b64encode(bytes(ct)).decode()}, headers=H(ta))
    check(r.status_code == 400 and "RSA-OAEP Decryption Failed" in r.json()["detail"], "Tampered token rejected: " + r.json()["detail"])
    r = c.post("/api/sharing/access-shared-data", json={"request_id": req_id, "encrypted_key": "not-base64!!"}, headers=H(ta))
    check(r.status_code == 400, "Garbage token rejected")
    check(c.post("/api/sharing/access-shared-data", json=body, headers=H(tb)).status_code == 403, "Owner cannot use requester endpoint")
    tc = c.post("/api/auth/register", json={"username": "eve_x", "password": "Eve123456"}).json()["access_token"]
    check(c.post("/api/sharing/access-shared-data", json=body, headers=H(tc)).status_code == 403, "Third party (Eve) blocked")

    print("== 7. Revoke (crypto-shredding) ==")
    check(c.post(f"/api/sharing/revoke/{req_id}", headers=H(tb)).json()["status"] == "REVOKED", "Revoked")
    check(c.post("/api/sharing/access-shared-data", json=body, headers=H(ta)).status_code == 409, "Token useless after revoke")
    check(c.get("/api/data/private", headers=H(tb)).json() == pii, "Owner's own data intact after revoke")

print("\nALL ASSIGNMENT 2 E2E CHECKS PASSED")
