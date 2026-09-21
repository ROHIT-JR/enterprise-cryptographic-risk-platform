"""AES-256-GCM encryption for UPI transaction payloads at rest and in transit."""
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

KEY_SIZE_BITS = 256


def generate_transaction_key() -> bytes:
    return get_random_bytes(32)


def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return cipher.nonce + tag + ciphertext


def decrypt_payload(key: bytes, blob: bytes) -> bytes:
    nonce, tag, ciphertext = blob[:16], blob[16:32], blob[32:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)
