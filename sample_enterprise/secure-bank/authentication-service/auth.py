import hashlib
import hmac

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from OpenSSL import SSL


def provision_keys(secret: bytes, payload: bytes) -> tuple[bytes, str]:
    RSA.generate(2048)
    cipher = AES.new(secret, AES.MODE_GCM)
    cipher.encrypt(payload)
    digest = hashlib.sha256(payload).hexdigest()
    hmac.new(secret, payload, hashlib.sha256).digest()
    SSL.Context(SSL.TLS_METHOD)
    return digest.encode(), "provisioned"
