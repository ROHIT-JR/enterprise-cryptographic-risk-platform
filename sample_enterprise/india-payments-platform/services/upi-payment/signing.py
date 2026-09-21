"""UPI transaction signing service - RSA-2048 digital signatures per NPCI spec."""
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes


def generate_signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def sign_transaction(private_key, transaction_payload: bytes) -> bytes:
    padder = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
    return private_key.sign(transaction_payload, padder, hashes.SHA256())


def verify_transaction(public_key, signature: bytes, transaction_payload: bytes) -> bool:
    try:
        public_key.verify(
            signature,
            transaction_payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
