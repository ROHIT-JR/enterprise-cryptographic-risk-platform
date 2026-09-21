"""OTP generation and verification via HMAC-SHA256 for Aadhaar-linked mobile authentication."""
import hmac
import hashlib


def generate_otp_token(secret: bytes, transaction_id: str) -> str:
    return hmac.new(secret, transaction_id.encode(), hashlib.sha256).hexdigest()


def verify_otp_token(secret: bytes, transaction_id: str, token: str) -> bool:
    expected = generate_otp_token(secret, transaction_id)
    return hmac.compare_digest(expected, token)
