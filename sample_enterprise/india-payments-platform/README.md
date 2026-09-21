# India Payments Platform (Demo)

A synthetic, India-specific enterprise codebase for ECDAT-X demos. It simulates
six services in a typical Indian digital-payments stack, deliberately mixing
modern and legacy cryptography so a scan produces a realistic risk profile.

| Service | Language | Cryptography |
|---|---|---|
| UPI Payment Service | Python | RSA-2048 signing, AES-256-GCM encryption |
| NPCI Gateway | Java | TLS 1.2, ECDSA (P-256) certificates |
| Aadhaar Auth Module | Python | SHA-256 biometric hashing, HMAC-SHA256 OTP |
| IMPS/NEFT Service | Java | 3DES legacy settlement encryption (deliberately vulnerable), SHA-1 checksum |
| Mobile Banking API | Node.js/TypeScript | HMAC-SHA256 JWT signing, AES-256-GCM refresh tokens |
| Core Banking Interface | C | OpenSSL, TLS 1.2 |

## Using this for a demo

See [`docs/demo-script.md`](../../docs/demo-script.md) for the full walkthrough:
zip this directory, upload it as a repository scan, then step through discovery,
risk, blast radius, the Mosca timeline, the migration roadmap, and the NQM
compliance report.
