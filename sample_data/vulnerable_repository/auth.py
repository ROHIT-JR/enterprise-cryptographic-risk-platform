from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
import hashlib


legacy_signing_key = RSA.generate(2048)
session_cipher = AES.new(b"0" * 32, AES.MODE_GCM)
password_digest = hashlib.sha1(b"legacy-password").hexdigest()

