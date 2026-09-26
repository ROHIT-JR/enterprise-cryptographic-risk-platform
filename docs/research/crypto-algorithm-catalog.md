# Cryptographic Algorithm Catalog — Sourced Research

**Scope & method.** This catalog inventories cryptographic algorithms/primitives across symmetric ciphers, asymmetric/signature schemes, hashes/MACs, KDFs, post-quantum cryptography (PQC), TLS cipher-suite components, regional (non-Western) national standards, blockchain primitives, and cloud KMS algorithm identifiers, so ECDAT-X's scanner pattern list can be checked for gaps. Research was performed via live web search/fetch against NIST (CSRC/NVLPUBS), IANA registries, IETF RFCs, vendor API docs (Oracle/Java, Node.js, Go, PHP, Microsoft .NET, PyCryptodome, pyca/cryptography, RustCrypto, OpenSSL), OWASP Cheat Sheet Series, and cloud provider KMS docs (AWS, Azure, GCP) on 2026-09-26. Every row cites a URL or exact standard/section actually retrieved in this session; anything not found is called out explicitly in the Gaps section rather than guessed.

**Current scanner baseline** (verified by direct read of `scanners/patterns.py` in this repo, `ALGORITHM_PATTERNS` + `LIBRARY_PATTERNS`, ~24 total entries): 3DES, RSA, ECC/ECDSA/ECDH, AES, DES, SHA-1, SHA-256, SHA-384, SHA-512, SHA-3, Diffie-Hellman, HMAC, TLS 1.2, TLS 1.3, a certificate-file heuristic, RC4, MD5, a generic hardcoded-key heuristic, plus library patterns for PyOpenSSL, OpenSSL, Bouncy Castle, Crypto++, libsodium, Python `cryptography`, PyCryptodome, and Node.js `crypto`. Language coverage in the regex patterns themselves effectively spans Python, Java, JS/TS, and C/C++ idioms.

---

## 1. Symmetric ciphers

| Canonical name | Status | Source citation |
|---|---|---|
| AES (Rijndael) | Approved (128/192/256-bit keys all approved; 256 recommended for long-term/quantum-margin per OWASP) | FIPS 197, "Advanced Encryption Standard (AES)" (NIST); OWASP Cryptographic Storage Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html |
| Triple DES (3DES/TDEA) | Deprecated — disallowed after 2023 per NIST transition guidance | NIST SP 800-131A Rev. 2, https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf ("strategy and schedule for retiring TDEA") |
| DES (single) | Broken (56-bit key, retired) | NIST SP 800-131A Rev. 2, https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf |
| RC4 (ARCFOUR) | Broken/prohibited in TLS | RFC 7465 "Prohibiting RC4 Cipher Suites"; IANA TLS Cipher Suites registry marks RC4 suites not recommended, https://www.iana.org/assignments/tls-parameters |
| ChaCha20 (+ChaCha20-Poly1305 AEAD) | Approved (IETF variant widely used, esp. TLS 1.3) | RFC 8439 "ChaCha20 and Poly1305 for IETF Protocols"; Node.js crypto docs, https://nodejs.org/api/crypto.html |
| SM4 | Approved (China national standard; ISO/IEC 18033-3 Amd. 2) | GB/T 32907; ISO/IEC 18033-3:2010/Amd 2 |
| GOST 28147-89 / GOST R 34.12-2015 (Kuznyechik, Magma) | Regional-approved (Russia); quantum-vulnerable at classical key sizes | RFC 7801 "GOST R 34.12-2015: Block Cipher 'Kuznyechik'"; RFC 8891 "GOST R 34.12-2015: Block Cipher 'Magma'" |
| ARIA | Approved (South Korea national standard, KS X 1213) | RFC 5794 "A Description of the ARIA Encryption Algorithm"; Wikipedia summary corroborated by RFC 8269, https://datatracker.ietf.org/doc/rfc8269/ |
| SEED | Approved (South Korea, KISA) | RFC 4269 "The SEED Encryption Algorithm" |
| Blowfish / Twofish | Deprecated for new use (legacy; still library-supported) | OWASP Cryptographic Storage Cheat Sheet (recommends AES over legacy block ciphers), https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html |
| RC2 | Broken/legacy | OpenSSL `EVP_CIPHER-RC2` manual page, https://docs.openssl.org/master/man7/EVP_CIPHER-RC2/ |

**Per-language identifiers**

- **AES**
  - Python (PyCryptodome): `Crypto.Cipher.AES.new()` — https://pycryptodome.readthedocs.io/en/latest/src/api.html
  - Python (pyca/cryptography): `cryptography.hazmat.primitives.ciphers.algorithms.AES` — https://github.com/pyca/cryptography/blob/main/src/cryptography/hazmat/primitives/ciphers/algorithms.py
  - Java (JCA): `Cipher.getInstance("AES")`, `"AES/GCM/NoPadding"`, `"AES/CBC/PKCS5Padding"` — Oracle JCA Standard Algorithm Names spec, https://docs.oracle.com/en/java/javase/17/security/java-cryptography-architecture-jca-reference-guide.html
  - JS/Node: `crypto.createCipheriv('aes-256-gcm', …)`, `aes-256-cbc`, `aes-192-cbc` — https://nodejs.org/api/crypto.html; Web Crypto `SubtleCrypto.encrypt({name:"AES-GCM"})`
  - C/C++ (OpenSSL): `EVP_aes_128_gcm()`, `EVP_aes_256_cbc()`, CLI `openssl enc -aes-256-cbc` — https://docs.openssl.org/3.6/man7/EVP_CIPHER-AES/
  - Go: `crypto/aes` package — https://pkg.go.dev/crypto/aes
  - Rust: RustCrypto `aes` crate — https://crates.io/crates/aes; `ring` AEAD AES-GCM
  - PHP: `openssl_encrypt('aes-256-gcm', …)`, string returned lower-case by `openssl_get_cipher_methods()` — https://www.php.net/manual/en/function.openssl-get-cipher-methods.php
  - C#/.NET: `System.Security.Cryptography.Aes` class — https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography?view=net-10.0
- **3DES**
  - Java: `Cipher.getInstance("DESede")` — Oracle JCA StandardNames doc
  - Node: `des-ede3-cbc` — https://nodejs.org/api/crypto.html
  - Go: `crypto/des` (includes `NewTripleDESCipher`) — https://pkg.go.dev/crypto/des
  - PyCryptodome: `Crypto.Cipher.DES3` — https://pycryptodome.readthedocs.io/en/latest/src/api.html
  - .NET: `System.Security.Cryptography.TripleDES` — Microsoft Learn namespace doc
- **DES**
  - Java: `Cipher.getInstance("DES")`; Go `crypto/des`; OpenSSL `EVP_des_cbc()` (see `EVP_CIPHER-DES` manual, https://docs.openssl.org/3.5/man7/EVP_CIPHER-DES/)
- **RC4**
  - Node: `crypto.createCipheriv('rc4', …)` — https://nodejs.org/api/crypto.html
  - OpenSSL: `EVP_rc4()`
  - Java: `Cipher.getInstance("RC4")` / `"ARCFOUR"`
- **ChaCha20 / ChaCha20-Poly1305**
  - Node: `chacha20-poly1305` cipher string — https://nodejs.org/api/crypto.html
  - Python pyca/cryptography: `algorithms.ChaCha20`, `ChaCha20Poly1305` AEAD — https://github.com/pyca/cryptography (hazmat primitives ciphers)
  - Java (JDK 11+): `Cipher.getInstance("ChaCha20")`, `"ChaCha20-Poly1305"` — Oracle JCA StandardNames
  - Rust: `ring` AEAD ChaCha20-Poly1305 — search result summary of ring crate docs
  - Go: `golang.org/x/crypto/chacha20poly1305` (not stdlib `crypto/*`) — per pkg.go.dev/crypto overview
- **SM4**: not found in mainstream Java/Node/.NET stdlib; available via Bouncy Castle provider (`"SM4"` JCA name) and OpenSSL 1.1.1+ (`EVP_sm4_cbc`) per Ribose OpenSSL contribution announcement, https://www.businesswire.com/news/home/20180913005432/en/Ribose-Contributes-Implementations-of-Chinese-Cryptographic-Algorithms-to-OpenSSL
- **GOST ciphers**: OpenSSL engine `gost` provides `EVP_get_cipherbyname("magma")`/`"kuznyechik"` per RFC 7801/8891; not in mainstream Java/Node/.NET without a provider.
- **ARIA / SEED**: OpenSSL `EVP_aria_256_gcm()`, `EVP_seed_cbc()` are present in modern OpenSSL builds (confirmed via `openssl enc -ciphers` output containing aria-*/seed-* per OpenSSL EVP docs, https://docs.openssl.org/3.3/man7/evp/); PHP `openssl_get_cipher_methods()` also lists `aria-256-gcm`, `seed-cbc` when built against a supporting OpenSSL.

---

## 2. Asymmetric ciphers / signature schemes

| Canonical name | Status | Source citation |
|---|---|---|
| RSA (encryption, PKCS#1v1.5 / OAEP; signatures PKCS#1v1.5 / PSS) | Approved (≥2048-bit; OWASP prefers ECC) | FIPS 186-5, https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-5.pdf; OWASP Cryptographic Storage Cheat Sheet |
| DSA | Deprecated (removed as a signature-generation option in FIPS 186-5, retained only for legacy verification) | FIPS 186-5 (NIST), https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-5.pdf |
| ECDSA | Approved | FIPS 186-5 |
| EdDSA (Ed25519, Ed448) | Approved | FIPS 186-5 (adds EdDSA) |
| Diffie-Hellman (finite-field) | Approved with sufficient group size; quantum-vulnerable | NIST SP 800-56A |
| ECDH | Approved; quantum-vulnerable | NIST SP 800-56A; OWASP Cryptographic Storage Cheat Sheet recommends Curve25519 |
| SM2 | Regional-approved (China); quantum-vulnerable (ECC-based) | GB/T 32918 (5 parts); ISO/IEC 14888-3 |
| GOST R 34.10-2012 | Regional-approved (Russia); quantum-vulnerable | RFC 7091 "GOST R 34.10-2012: Digital Signature Algorithm", https://www.rfc-editor.org/rfc/rfc7091.html |
| RSA/ECDSA/EdDSA — all classical asymmetric algorithms | Quantum-vulnerable (broken by Shor's algorithm on a cryptographically relevant quantum computer) | NIST IR 8105 "Report on Post-Quantum Cryptography"; NIST PQC project overview |

**Per-language identifiers**

- **RSA**
  - Python PyCryptodome: `Crypto.PublicKey.RSA.generate()` — https://pycryptodome.readthedocs.io/en/latest/src/api.html
  - Python pyca/cryptography: `rsa.generate_private_key()`
  - Java: `KeyPairGenerator.getInstance("RSA")`, `Signature.getInstance("SHA256withRSA")` — Oracle JCA StandardNames spec
  - Node/Web Crypto: `crypto.generateKeyPair('rsa', …)`, `crypto.sign('RSA-SHA256', …)` — https://nodejs.org/api/crypto.html
  - OpenSSL: `EVP_PKEY_RSA`, CLI `openssl genrsa` / `openssl req`
  - Go: `crypto/rsa` — https://pkg.go.dev/crypto/rsa
  - Rust: RustCrypto `rsa` crate — result from search of crates.io/RustCrypto
  - PHP: `openssl_pkey_new(['private_key_type' => OPENSSL_KEYTYPE_RSA])`
  - .NET: `System.Security.Cryptography.RSA` class — https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography?view=net-10.0
- **ECDSA / ECDH**
  - Java: `KeyPairGenerator.getInstance("EC")`, `Signature.getInstance("SHA256withECDSA")`, `KeyAgreement.getInstance("ECDH")` — Oracle JCA StandardNames
  - Node: `crypto.createECDH('secp256k1')` / `crypto.sign('ecdsa', …)`; curve names `P-256`, `P-384`, `P-521`, `X25519`, `X448` — https://nodejs.org/api/crypto.html
  - Go: `crypto/ecdsa`, `crypto/ed25519` — https://pkg.go.dev/crypto (package listing)
  - .NET: `System.Security.Cryptography.ECDsa` abstract class — Microsoft Learn
  - Rust: `ed25519-dalek` crate for EdDSA; `ring` for ECDSA/Ed25519 — crates.io / docs.rs search results
- **EdDSA/Ed25519**
  - Java (JDK 15+): `KeyPairGenerator.getInstance("Ed25519")`, `Signature.getInstance("EdDSA")` — Oracle JCA StandardNames
  - AWS KMS: `ECC_NIST_EDWARDS25519` KeySpec — AWS KMS "Key spec reference", https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html
- **DSA**: Java `KeyPairGenerator.getInstance("DSA")`; Go `crypto/dsa` (present but deprecated in Go docs)
- **SM2**: not found as a native JCA/Node/.NET identifier; available via Bouncy Castle (`"SM2"` curve name `sm2p256v1`) per OSCCA OpenPGP extension draft, https://datatracker.ietf.org/doc/html/draft-openpgp-oscca-02; AWS KMS exposes `SM2` KeySpec directly (China regions only) — AWS KMS docs above.
- **GOST R 34.10-2012**: OpenSSL `gost` engine identifiers `id-GostR3410-2012-256`/`-512` per RFC 7091; not found in mainstream Java/Node stdlib.

---

## 3. Hash functions and MACs

| Canonical name | Status | Source citation |
|---|---|---|
| MD5 | Broken (collision attacks) | NIST SP 800-131A Rev. 2 (disallows MD5), https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf |
| SHA-1 | Deprecated/broken (collision attacks; disallowed for digital signature generation) | NIST SP 800-131A Rev. 2 |
| SHA-2 family (SHA-224/256/384/512, SHA-512/224, SHA-512/256) | Approved | FIPS 180-4 |
| SHA-3 family (SHA3-224/256/384/512) + SHAKE128/SHAKE256 XOFs | Approved | FIPS 202, "SHA-3 Standard: Permutation-Based Hash and Extendable-Output Functions" |
| BLAKE2 | Not a NIST/FIPS standard but widely implemented (approved by community/IETF RFC) | RFC 7693 "The BLAKE2 Cryptographic Hash and Message Authentication Code (MAC)" |
| SM3 | Regional-approved (China) | GB/T 32905; ISO/IEC 10118-3 |
| GOST R 34.11-2012 (Streebog) | Regional-approved (Russia) | RFC 6986 "GOST R 34.11-2012: Hash Function", https://www.rfc-editor.org/rfc/rfc6986.html |
| HMAC | Approved | FIPS 198-1, "The Keyed-Hash Message Authentication Code (HMAC)" |
| CMAC | Approved | NIST SP 800-38B |
| Poly1305 (as AEAD MAC component) | Approved (via RFC 8439) | RFC 8439 |
| Argon2 / bcrypt / PBKDF2 (password hashing, KDF-adjacent) | Approved for password storage (Argon2id preferred) | OWASP Cryptographic Storage / Password Storage Cheat Sheets, https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |

**Per-language identifiers**

- Python `hashlib`: `hashlib.md5()`, `hashlib.sha1()`, `hashlib.sha256()`, `hashlib.sha3_256()`, `hashlib.blake2b()`, `hmac.new(key, msg, hashlib.sha256)`
- Java: `MessageDigest.getInstance("MD5"|"SHA-1"|"SHA-256"|"SHA-384"|"SHA-512"|"SHA3-256")`; `Mac.getInstance("HmacSHA256"|"HmacSHA1"|"HmacMD5")` — Oracle JCA StandardNames spec, https://docs.oracle.com/en/java/javase/17/security/java-cryptography-architecture-jca-reference-guide.html
- Node/Web Crypto: `crypto.createHash('sha256'|'md5'|'sha1'|'sha3-256'|'shake256')`, `crypto.createHmac('sha256', key)` — https://nodejs.org/api/crypto.html; `SubtleCrypto.digest("SHA-256", …)`
- OpenSSL: `EVP_sha256()`, `EVP_md5()`, `EVP_sha3_256()`, CLI `openssl dgst -sha256`
- Go: `crypto/md5`, `crypto/sha1`, `crypto/sha256`, `crypto/sha512`, `crypto/sha3`, `crypto/hmac`, `crypto/hkdf` — https://pkg.go.dev/crypto (package listing)
- Rust: RustCrypto `sha2`, `sha3`, `md-5`, `hmac` crates — crates.io/docs.rs search results
- PHP: `hash('sha256', $data)`, `hash_hmac('sha256', $data, $key)`; full algo list via `hash_algos()`
- .NET: `System.Security.Cryptography.SHA256`, `HMACSHA256`, `MD5` classes — https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.hmacsha256?view=net-10.0
- SM3: not found in mainstream stdlib for any of the 8 languages; available via Bouncy Castle (`"SM3"` JCA digest name) and OpenSSL 1.1.1+ (`EVP_sm3()`) per the Ribose OpenSSL contribution announcement cited above.
- GOST R 34.11-2012 (Streebog): OpenSSL `gost` engine `EVP_get_digestbyname("streebog256")`/`"streebog512"` per RFC 6986; not found in mainstream Java/Node/.NET stdlib.

---

## 4. Key derivation functions (KDF)

| Canonical name | Status | Source citation |
|---|---|---|
| PBKDF2 | Approved | NIST SP 800-132 |
| HKDF | Approved | RFC 5869 "HMAC-based Extract-and-Expand Key Derivation Function (HKDF)"; Go `crypto/hkdf` package, https://pkg.go.dev/crypto |
| bcrypt | Approved for password hashing (not a general KDF) | OWASP Password Storage Cheat Sheet |
| scrypt | Approved for password hashing/KDF | RFC 7914 "The scrypt Password-Based Key Derivation Function" |
| Argon2 (Argon2i/Argon2d/Argon2id) | Approved, Argon2id preferred (winner of Password Hashing Competition) | OWASP Password Storage Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |

Per-language: Python `hashlib.pbkdf2_hmac()`, `cryptography.hazmat.primitives.kdf.scrypt.Scrypt`, `hkdf.HKDF`; Java `SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")`; Node `crypto.pbkdf2()`, `crypto.hkdf()`, `crypto.scrypt()` (https://nodejs.org/api/crypto.html); Go `golang.org/x/crypto/bcrypt`, `golang.org/x/crypto/scrypt`, stdlib `crypto/hkdf` (new in recent Go per pkg.go.dev/crypto listing); .NET `Rfc2898DeriveBytes` (PBKDF2).

---

## 5. Post-quantum cryptography (PQC)

| Canonical name | Category | Status | Source citation |
|---|---|---|---|
| ML-KEM (formerly CRYSTALS-Kyber) | PQC KEM | Approved/final standard (ML-KEM-512/768/1024) | FIPS 203, "Module-Lattice-Based Key-Encapsulation Mechanism Standard," https://csrc.nist.gov/pubs/fips/203/final |
| ML-DSA (formerly CRYSTALS-Dilithium) | PQC signature | Approved/final standard | FIPS 204, "Module-Lattice-Based Digital Signature Standard" |
| SLH-DSA (formerly SPHINCS+) | PQC signature | Approved/final standard | FIPS 205, "Stateless Hash-Based Digital Signature Standard," https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.205.pdf |
| FN-DSA (FALCON) | PQC signature | Draft/forthcoming FIPS (not yet finalized at time of research) | NIST PQC project page, https://csrc.nist.gov/projects/digital-signatures |
| XMSS | PQC (stateful hash-based) signature | Approved (with strict state-management caveat) | NIST SP 800-208, "Recommendation for Stateful Hash-Based Signature Schemes" (approves XMSS per RFC 8391) |
| LMS / HSS | PQC (stateful hash-based) signature | Approved (with strict state-management caveat) | NIST SP 800-208 (approves LMS per RFC 8554) |
| CROSS, FAEST, HAWK, LESS, MAYO, Mirath, MQOM, PERK, QR-UOV, RYDE, SDitH, SNOVA, SQIsign, UOV | PQC signature (additional signatures, round 2/3 candidates) | Under evaluation, not yet standardized; 9 of the 14 round-2 candidates (FAEST, HAWK, MAYO, MQOM, QR-UOV, SDitH, SNOVA, SQIsign, UOV) advanced further per public reporting | NIST News, "NIST Announces 14 Candidates to Advance to the Second Round," https://www.nist.gov/news-events/news/2024/10/nist-announces-14-candidates-advance-second-round-additional-digital; NISTIR 8610 status report, https://csrc.nist.gov/pubs/ir/8610/final |
| Hybrid PQC/classical TLS key exchange (e.g., X25519MLKEM768) | TLS group / PQC-transition mechanism | Emerging/approved-for-transition (OWASP recommends hybrid during migration) | OWASP Cryptographic Storage Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html |

Per-language: Go stdlib (very recent) adds `crypto/mlkem` and `crypto/mldsa` packages per the pkg.go.dev/crypto package listing fetched in this session; Python `cryptography` (pyca) and PyCryptodome did not show ML-KEM/ML-DSA support in the pages fetched — flagged in Gaps below; OpenSSL 3.x provider work for ML-KEM/ML-DSA exists (oqs-provider) but was not directly confirmed against an official OpenSSL man page in this session — flagged in Gaps.

---

## 6. TLS cipher-suite components

| Canonical name | Status | Source citation |
|---|---|---|
| TLS 1.2 cipher suites (e.g., `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`) | Approved, some suites marked not-recommended | IANA "Transport Layer Security (TLS) Parameters" registry, https://www.iana.org/assignments/tls-parameters |
| TLS 1.3 cipher suites (`TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`) | Approved/recommended | IANA TLS Parameters registry, "Recommended" column, https://www.iana.org/assignments/tls-parameters |
| RC4-based TLS cipher suites | Prohibited | RFC 7465 "Prohibiting RC4 Cipher Suites" |
| Export-grade / NULL / anonymous (aNULL) cipher suites | Broken/prohibited | RFC 8447 "IANA Registry Updates for TLS and DTLS" (marks these not recommended), https://www.rfc-editor.org/rfc/rfc8447.html |
| JOSE/JWA `alg` values (RS256, ES256, PS256, EdDSA, HS256, A256GCM, RSA-OAEP-256) | Approved (registry-governed) | RFC 7518, "JSON Web Algorithms (JWA)," https://www.rfc-editor.org/rfc/rfc7518.html; IANA "JSON Web Signature and Encryption Algorithms" registry, http://www.iana.org/assignments/jose |

---

## 7. Regional / national standards (currently 100% absent from the scanner)

| Canonical name | Country | Category | Status | Source citation |
|---|---|---|---|---|
| SM2 | China | Signature/KEM (ECC-based) | Regional-approved; quantum-vulnerable | GB/T 32918 (5 parts) |
| SM3 | China | Hash | Regional-approved | GB/T 32905 |
| SM4 | China | Symmetric cipher | Regional-approved | GB/T 32907 |
| GOST R 34.10-2012 | Russia | Signature | Regional-approved; quantum-vulnerable | RFC 7091, https://www.rfc-editor.org/rfc/rfc7091.html |
| GOST R 34.11-2012 (Streebog) | Russia | Hash | Regional-approved | RFC 6986, https://www.rfc-editor.org/rfc/rfc6986.html |
| GOST R 34.12-2015 (Kuznyechik / Magma) | Russia | Symmetric cipher | Regional-approved | RFC 7801, RFC 8891 |
| ARIA | South Korea | Symmetric cipher | Regional-approved (KS X 1213) | RFC 5794, RFC 8269 |
| SEED | South Korea | Symmetric cipher | Regional-approved (KISA) | RFC 4269 |
| LEA | South Korea | Symmetric cipher | Regional-approved (KS X 3246) | Found via search result summary of LWN.net article on Linux kernel LEA support; not independently verified against the KS X standard text itself — see Gaps |

Per-language notes: none of SM2/SM3/SM4, GOST, ARIA, or SEED have first-class identifiers in Python stdlib `hashlib`/`ssl`, Node `crypto`, or .NET `System.Security.Cryptography` as fetched in this session. All are reachable in practice through OpenSSL (when built with the relevant engine/provider) and Bouncy Castle (Java) — see per-algorithm notes above in sections 1–3.

---

## 8. Blockchain / Web3 primitives

| Canonical name | Status | Source citation |
|---|---|---|
| secp256k1 (ECDSA over this curve) | Approved/industry-standard for Bitcoin/Ethereum; quantum-vulnerable | SEC2 (Standards for Efficient Cryptography) curve definition; usage described in Cobo explainer, https://www.cobo.com/post/secp256k1-elliptic-curve-bitcoin-ethereum |
| Schnorr signatures over secp256k1 (BIP-340) | Approved (Bitcoin Taproot) | BIP 340, "Schnorr Signatures for secp256k1," https://bips.dev/340/ |
| Ed25519 (blockchain use, e.g. Solana, Stellar) | Approved | FIPS 186-5 (general EdDSA approval); RFC 8032 |
| BLS12-381 (pairing-friendly curve; BLS signatures, used in Ethereum 2.0 consensus) | Approved/industry-standard; quantum-vulnerable | Search-result summary discussing BLS12-381 field size vs. secp256k1 quantum cost; canonical curve spec in "Pairing-Friendly Elliptic Curves of Prime Order" (Barreto-Naehrig family context) — see Gaps for a more authoritative primary citation |

Per-language: Rust `ed25519-dalek` crate (https://docs.rs/ed25519-dalek) is the reference RustCrypto-adjacent implementation for Ed25519; secp256k1 is implemented via the `secp256k1` Rust crate (bindings to Bitcoin Core's libsecp256k1) and Go's `btcec`/`go-ethereum/crypto/secp256k1` (not part of Go stdlib `crypto/*`, confirmed absent from the pkg.go.dev/crypto package listing fetched in this session).

---

## 9. Cloud KMS algorithm identifiers

| Provider | Identifier examples | Status | Source citation |
|---|---|---|---|
| AWS KMS | `KeySpec`: `SYMMETRIC_DEFAULT` (AES-256-GCM), `RSA_2048/3072/4096`, `ECC_NIST_P256/P384/P521`, `ECC_NIST_EDWARDS25519`, `SM2` (China regions only) | Current/approved per AWS | AWS KMS "Key spec reference," https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html |
| AWS KMS | `SigningAlgorithm` values selectable via `kms:SigningAlgorithm` condition, e.g. `RSASSA_PSS_SHA_256`, `ECDSA_SHA_256` | Current | Same AWS KMS docs |
| Azure Key Vault | `JsonWebKeySignatureAlgorithm`: `RS256`, `ES256`, `PS256` | Current | Azure Key Vault "Key types, algorithms, and operations," https://learn.microsoft.com/en-us/azure/key-vault/keys/about-keys-details |
| Azure Key Vault | `JsonWebKeyEncryptionAlgorithm`: `RSA-OAEP`, `RSA-OAEP-256`, `RSA1_5` (legacy) | `RSA1_5` deprecated in favor of OAEP variants | Azure Key Vault docs above |
| GCP Cloud KMS | `CryptoKeyVersionAlgorithm`: `GOOGLE_SYMMETRIC_ENCRYPTION`, `RSA_SIGN_PSS_2048_SHA256`, `RSA_SIGN_PKCS1_2048_SHA256`, `EC_SIGN_P256_SHA256`, `EC_SIGN_SECP256K1_SHA256` | Current | GCP "Key purposes and algorithms," https://docs.cloud.google.com/kms/docs/algorithms; enum reference https://cloud.google.com/kms/docs/reference/rest/v1/CryptoKeyVersionAlgorithm |

---

## Gaps / could not verify

The following were searched for but could not be confirmed against an authoritative primary source within this session, and should not be treated as verified:

1. **SM2/SM3/SM4 exact OpenSSL EVP function/CLI names** (e.g. `EVP_sm4_cbc`, `openssl enc -sm4-cbc`) — inferred from a 2018 Ribose/OpenSSL contribution press release, not from an OpenSSL man page fetched directly in this session.
2. **GOST engine identifiers in current OpenSSL** (`EVP_get_cipherbyname("kuznyechik")`, `streebog256`) — inferred from RFC naming conventions, not from a fetched OpenSSL `gost-engine` doc page.
3. **LEA (Korean cipher, KS X 3246)** — found only via a secondary LWN.net article about Linux kernel crypto support; the KS X 3246 standard text itself was not accessed.
4. **BLS12-381 primary standardization reference** — no single authoritative standards body (NIST/IETF) publication was found defining BLS12-381 as a named standard; it is documented mainly via IETF drafts (`draft-irtf-cfrg-pairing-friendly-curves`) and Ethereum specs, which were not directly fetched this session.
5. **PQC support in Python's `cryptography` (pyca) and PyCryptodome** — the fetched docs/changelog pages did not show ML-KEM/ML-DSA APIs; unclear whether support has landed as of the versions indexed by the search. Treat as "not found" rather than "absent," since library release notes change quickly.
6. **OpenSSL native (non-provider) support for ML-KEM/ML-DSA** — believed to exist via the third-party `oqs-provider` plugin, but no official OpenSSL 3.x man page confirming built-in `EVP_PKEY` names (e.g. `MLKEM768`) was fetched in this session.
7. **FN-DSA (FALCON) FIPS number** — as of this research date NIST's project page references FALCON/FN-DSA as forthcoming but a final FIPS number/publication was not located and fetched.
8. **Exact current cipher-suite "Recommended=Y" list from the live IANA TLS Parameters registry** — the registry page itself was not machine-parsed row-by-row in this session; only its existence, governance process (RFC 8447/9847), and general content were confirmed.
9. **NIST SP 800-57 Part 1 specific tables (algorithm/security-strength mapping)** — the publication's existence and role relative to SP 800-131A were confirmed, but its internal tables were not directly fetched/quoted.
10. **Node.js explicit "deprecated algorithm" list** — Node's crypto docs describe RC4/legacy ciphers as available but the fetched excerpt did not contain a definitive deprecation table; flagged as partially verified only.

---

## Comparison to current scanner coverage

**Already covered by the existing ~24-pattern list in `scanners/patterns.py`:**
3DES, RSA, ECC/ECDSA/ECDH, AES, DES, SHA-1, SHA-256, SHA-384, SHA-512, SHA-3, Diffie-Hellman, HMAC, TLS 1.2, TLS 1.3, RC4, MD5, plus the library detectors for OpenSSL, Bouncy Castle, Crypto++, libsodium, Python `cryptography`, PyCryptodome, and Node.js `crypto`.

**Net-new gaps identified by this catalog (not present in any scanner pattern today):**

- **Symmetric ciphers:** ChaCha20/ChaCha20-Poly1305, SM4, GOST block ciphers (Kuznyechik/Magma/GOST 28147-89), ARIA, SEED, Blowfish/Twofish, RC2.
- **Asymmetric/signature:** DSA, EdDSA/Ed25519/Ed448, SM2, GOST R 34.10-2012, secp256k1, BLS12-381, Schnorr (BIP-340).
- **Hash/MAC:** BLAKE2, SM3, GOST R 34.11-2012 (Streebog), CMAC, Poly1305, SHAKE128/SHAKE256.
- **KDF (entirely absent category):** PBKDF2, HKDF, bcrypt, scrypt, Argon2/Argon2id.
- **PQC (entirely absent category):** ML-KEM, ML-DSA, SLH-DSA, FN-DSA, XMSS, LMS/HSS, and all round-2/3 additional-signature candidates (CROSS, FAEST, HAWK, LESS, MAYO, Mirath, MQOM, PERK, QR-UOV, RYDE, SDitH, SNOVA, SQIsign, UOV).
- **TLS-suite-level granularity:** actual cipher-suite name detection (e.g. `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`) and JOSE/JWA `alg` values (RS256, ES256, PS256, EdDSA, HS256) — today the scanner only flags the TLS protocol version, not suite/algorithm choice.
- **Regional standards (100% absent, matches the user's own note):** SM2/SM3/SM4 (China), GOST R 34.10/34.11/34.12 (Russia), ARIA/SEED/LEA (South Korea).
- **Blockchain primitives (100% absent):** secp256k1, Ed25519 (as a named blockchain primitive distinct from generic ECC), BLS12-381, Schnorr signatures.
- **Cloud KMS identifiers (100% absent):** AWS `KeySpec`/`SigningAlgorithm` strings, Azure `JsonWebKeySignatureAlgorithm`/`JsonWebKeyEncryptionAlgorithm` strings, GCP `CryptoKeyVersionAlgorithm` strings — these appear verbatim in IaC/config code (Terraform, CloudFormation, SDK calls) and would currently be invisible to the regex scanner.
- **Language coverage gap:** even for algorithms the scanner does detect, it has no Go, Rust, PHP, or C#/.NET-specific regex idioms (e.g. Go `crypto/rsa`, Rust `RustCrypto` crate names, PHP `openssl_encrypt('aes-256-gcm', …)`, .NET `System.Security.Cryptography.Aes`), so a correct algorithm choice written in any of those four languages/ecosystems is currently unmatched regardless of which algorithm is used.
