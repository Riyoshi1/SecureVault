# 🛡️ SecureVault — Aplikasi Web Kriptografi Terapan (Tugas Besar Keamanan Informasi)

Aplikasi web *full-stack* untuk penyimpanan data pribadi (PII) sesuai **UU PDP No. 27 Tahun 2022 & GDPR EU** serta enkripsi berkas multi-format (`JPG/PNG`, `PDF/DOC/XLS`, `MP4`) menggunakan tiga algoritma kriptografi simetris yang diajarkan pada perkuliahan **Keamanan Informasi**:
1. **AES-256-CBC** (*Advanced Encryption Standard* — Block Cipher SPN 128-bit block, 256-bit key)
2. **DES-CBC** (*Data Encryption Standard* — Feistel Cipher 64-bit block, 56-bit effective key + 8 parity bits)
3. **RC4 (ARC4)** (*Rivest Cipher 4* — Stream Cipher KSA + PRGA dengan Nonce & Drop-3072)

---

## 📚 Pemetaan Materi Perkuliahan Keamanan Informasi (Modul 01 – 05)

| Modul Perkuliahan | Konsep Teoretis di Kelas | Implementasi Nyata pada Kode *SecureVault* |
| :--- | :--- | :--- |
| **01 - Introduction** | **CIA Triad** (*Confidentiality, Integrity, Availability*), *Authentication*, & Regulasi Privasi Data | • **Confidentiality:** Seluruh PII & file disimpan sebagai *ciphertext*.<br>• **Integrity:** Skema *Encrypt-then-MAC* (`HMAC-SHA256`) mencegah modifikasi *ciphertext*.<br>• **Authentication:** Password hashing `bcrypt` + derivasi kunci `PBKDF2-HMAC-SHA256` (600.000 iterasi) & pemisahan kunci `HKDF` (`app/utils/security.py`). |
| **02 - Classical Encryption & DES** | *Confusion & Diffusion* (Claude Shannon), Struktur **Feistel Cipher** 16-putaran, blok 64-bit (8 byte), kunci 56-bit + 8 bit *odd parity* | • Diimplementasikan pada `app/crypto/des_cipher.py`.<br>• Fungsi `adjust_key_parity()` mengatur *Least Significant Bit* (LSB) tiap byte kunci agar memenuhi *odd parity* sesuai standar FIPS 46-3.<br>• Menggunakan mode **CBC** + *PKCS#5 Padding* dan IV acak 8-byte. |
| **03 - Advanced Encryption Standard (AES)** | Struktur **SPN (*Substitution-Permutation Network*)** di $GF(2^8)$, *State Matrix* $4\times 4$ byte (128-bit), 14 putaran (kunci 256-bit): `SubBytes`, `ShiftRows`, `MixColumns`, `AddRoundKey` | • Diimplementasikan pada `app/crypto/aes_cipher.py`.<br>• Menggunakan kunci 256-bit (32 byte) dengan mode **CBC** (*Cipher Block Chaining*), *PKCS#7 Padding* ke kelipatan 16 byte, dan IV acak 16-byte per enkripsi. |
| **04 - AES Decryption & Modes of Operation** | Transformasi invers (`InvShiftRows`, `InvSubBytes`, `AddRoundKey`, `InvMixColumns`), bahaya mode **ECB**, serta persamaan mode **CBC** | • **Larangan Mutlak ECB:** Mode ECB tidak digunakan karena blok *plaintext* identik menghasilkan blok *ciphertext* identik.<br>• **CBC Enkripsi:** $C_i = E_K(P_i \oplus C_{i-1})$ dengan $C_0 = \text{IV}$.<br>• **CBC Dekripsi:** $P_i = D_K(C_i) \oplus C_{i-1}$.<br>• Verifikasi `HMAC-SHA256` dilakukan **sebelum** dekripsi untuk menangkal *Padding Oracle Attack*. |
| **05 - Stream Cipher (RC4)** | Pembangkitan *keystream* byte-demi-byte melalui **KSA** (*Key Scheduling Algorithm*) & **PRGA** (*Pseudo-Random Generation Algorithm*): $C_i = P_i \oplus k_i$ dan $P_i = C_i \oplus k_i$ | • Diimplementasikan pada `app/crypto/rc4_cipher.py`.<br>• Tanpa *padding* (ukuran *ciphertext* murni = ukuran *plaintext*).<br>• **Mitigasi Key Reuse (Two-Time Pad):** Menggunakan *random Nonce* 16-byte untuk menurunkan kunci unik per pesan via `HMAC-SHA256(base_key, nonce)[:16]`.<br>• **Mitigasi Serangan FMS:** Membuang 3.072 byte pertama *keystream* (`RC4-drop[3072]`). |

---

## 🚀 Cara Menjalankan Aplikasi

### 1. Menjalankan Backend (Python FastAPI — Port `8000`)
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
* Dokumentasi Swagger UI interaktif dapat diakses di: `http://localhost:8000/docs`
* Untuk menjalankan skrip benchmark langsung melalui terminal (CLI):
  ```powershell
  cd backend
  python -m app.benchmark
  ```

### 2. Menjalankan Frontend (Next.js + TailwindCSS — Port `3000`)
Buka terminal baru:
```powershell
cd frontend
npm install
npm run dev
```
* Buka aplikasi web di browser: `http://localhost:3000`
