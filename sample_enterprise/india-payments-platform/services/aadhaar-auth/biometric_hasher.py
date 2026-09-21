"""Aadhaar biometric template hashing - SHA-256 per UIDAI data protection guidelines."""
import hashlib


def hash_biometric_template(template_bytes: bytes) -> str:
    return hashlib.sha256(template_bytes).hexdigest()


def hash_iris_scan(iris_bytes: bytes) -> str:
    digest = hashlib.new("sha256")
    digest.update(iris_bytes)
    return digest.hexdigest()
