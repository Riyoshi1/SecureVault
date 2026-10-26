"""
Benchmark Module - Encryption/Decryption Performance Analysis

This module measures and compares the performance of AES-CBC, DES-CBC, and RC4
for both encryption and decryption operations.

Methodology:
1. Generate random test data of specified size
2. For each algorithm, perform N iterations of encrypt + decrypt
3. Measure wall-clock time for each operation using time.perf_counter()
   (highest resolution timer available)
4. Calculate average, total, and per-operation times
5. Record ciphertext sizes for overhead comparison

This data is used for the academic analysis report comparing:
- Running time differences between algorithms
- Ciphertext size overhead (block cipher padding vs stream cipher)
- Scalability with different input sizes
"""
import time
import os
from app.crypto.engine import CryptoEngine, ALGORITHMS
from app.utils.security import derive_algorithm_keys
from app.schemas import BenchmarkResultItem, CipherInspectItem, CipherInspectResponse


def inspect_ciphers(plaintext_str: str) -> CipherInspectResponse:
    """
    Encrypt a sample plaintext string using AES-256-CBC, DES-CBC, and RC4,
    and decompose the resulting binary structure into IV/Nonce, Ciphertext body,
    Padding overhead, and HMAC-SHA256 tag for academic comparison.
    """
    pt_bytes = plaintext_str.encode("utf-8")
    test_master_key = os.urandom(32)
    keys = derive_algorithm_keys(test_master_key)
    items: list[CipherInspectItem] = []

    specs = {
        "AES-CBC": {"mode": "CBC (Cipher Block Chaining) + PKCS#7", "block_bits": 128, "key_bits": 256, "iv_len": 16},
        "DES-CBC": {"mode": "CBC (Feistel 16-Round) + PKCS#5", "block_bits": 64, "key_bits": 56, "iv_len": 8},
        "RC4": {"mode": "Stream Cipher (KSA + PRGA Drop-3072)", "block_bits": 8, "key_bits": 128, "iv_len": 16},
    }

    for algo in ALGORITHMS:
        spec = specs[algo]
        iv_len = spec["iv_len"]

        t0 = time.perf_counter()
        blob = CryptoEngine.encrypt(pt_bytes, algo, keys)
        t1 = time.perf_counter()
        dec = CryptoEngine.decrypt(blob, algo, keys)
        t2 = time.perf_counter()
        assert dec == pt_bytes

        iv_or_nonce = blob[:iv_len]
        hmac_tag = blob[-32:]
        ct_body = blob[iv_len:-32]
        padding_len = len(ct_body) - len(pt_bytes)

        items.append(CipherInspectItem(
            algorithm=algo,
            mode=spec["mode"],
            block_size_bits=spec["block_bits"],
            key_size_bits=spec["key_bits"],
            plaintext_size_bytes=len(pt_bytes),
            total_output_bytes=len(blob),
            iv_or_nonce_hex=iv_or_nonce.hex(),
            iv_or_nonce_bytes=len(iv_or_nonce),
            ciphertext_hex=ct_body.hex(),
            ciphertext_bytes=len(ct_body),
            padding_bytes=padding_len,
            hmac_hex=hmac_tag.hex(),
            hmac_bytes=len(hmac_tag),
            encrypt_time_ms=round((t1 - t0) * 1000, 4),
            decrypt_time_ms=round((t2 - t1) * 1000, 4),
        ))

    return CipherInspectResponse(
        plaintext=plaintext_str,
        plaintext_hex=pt_bytes.hex(),
        items=items,
    )

def run_benchmark(data_size_kb: int = 100, iterations: int = 10) -> list[BenchmarkResultItem]:
    """
    Run encryption/decryption benchmarks for all three algorithms.
    
    Args:
        data_size_kb: Size of test data in kilobytes
        iterations: Number of encrypt/decrypt cycles per algorithm
    
    Returns:
        List of BenchmarkResultItem with timing results
    """
    # Generate random test data
    data_size_bytes = data_size_kb * 1024
    test_data = os.urandom(data_size_bytes)
    
    # Generate test keys (using a fixed test password and salt)
    # This is only for benchmarking - NOT used for real data
    test_master_key = os.urandom(32)
    keys = derive_algorithm_keys(test_master_key)
    
    results = []
    
    for algorithm in ALGORITHMS:
        encrypt_times = []
        decrypt_times = []
        ciphertext_size = 0
        
        for i in range(iterations):
            # Measure encryption time
            start = time.perf_counter()
            encrypted = CryptoEngine.encrypt(test_data, algorithm, keys)
            end = time.perf_counter()
            encrypt_times.append((end - start) * 1000)  # Convert to ms
            
            ciphertext_size = len(encrypted)
            
            # Measure decryption time
            start = time.perf_counter()
            decrypted = CryptoEngine.decrypt(encrypted, algorithm, keys)
            end = time.perf_counter()
            decrypt_times.append((end - start) * 1000)
            
            # Verify correctness
            assert decrypted == test_data, f"{algorithm}: Decrypted data doesn't match original!"
        
        results.append(BenchmarkResultItem(
            algorithm=algorithm,
            encrypt_avg_ms=round(sum(encrypt_times) / len(encrypt_times), 4),
            decrypt_avg_ms=round(sum(decrypt_times) / len(decrypt_times), 4),
            encrypt_total_ms=round(sum(encrypt_times), 4),
            decrypt_total_ms=round(sum(decrypt_times), 4),
            data_size_bytes=data_size_bytes,
            iterations=iterations,
            ciphertext_size_bytes=ciphertext_size,
        ))
    
    return results


if __name__ == "__main__":
    """Run benchmark from command line for quick analysis."""
    import json
    
    print("="*70)
    print("SecureVault Encryption Benchmark")
    print("="*70)
    
    # Test with different data sizes
    for size_kb in [1, 10, 100, 1000]:
        print(f"\n--- Data Size: {size_kb} KB ---")
        results = run_benchmark(data_size_kb=size_kb, iterations=20)
        
        for r in results:
            print(f"  {r.algorithm:8s} | "
                  f"Encrypt: {r.encrypt_avg_ms:8.4f} ms avg | "
                  f"Decrypt: {r.decrypt_avg_ms:8.4f} ms avg | "
                  f"Ciphertext: {r.ciphertext_size_bytes} bytes")
    
    print("\n" + "="*70)
    print("Benchmark complete.")
