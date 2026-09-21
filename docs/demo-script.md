# Demo Script: India Payments Platform

A guided walkthrough for presenting ECDAT-X with an India-specific scenario:
a synthetic UPI/NPCI payments stack instead of the generic SecureBank demo.
India processes 10B+ UPI transactions a month — showing quantum risk against
that kind of payment infrastructure is a much more compelling story for an
Indian audience than a generic bank.

## Numbers in this script are real, not scripted

Every figure below came from actually running ECDAT-X's own scanner and risk
engine against [`sample_enterprise/india-payments-platform`](../sample_enterprise/india-payments-platform/),
not from hand-written demo data. Re-running the scan will reproduce the same
counts (give or take engine improvements landing on `main` after this was
written).

**A few of the issue's original placeholder numbers ("12 quantum-vulnerable
algorithms", "89% of services affected") are not reproduced here.** The
current algorithm risk database only classifies RSA, ECC/ECDH, Diffie-Hellman,
AES-128/256, SHA-256, ML-KEM and ML-DSA as quantum-relevant (see
`risk_engine/algorithm_risks.json`); 3DES, SHA-1, SHA-384 and bare HMAC fall
back to an "unknown" classification until that database is expanded (tracked
separately). Blast-radius percentages also depend on a multi-service
dependency graph that a single-repository scan doesn't produce on its own —
see the note in Step 4. This script uses the numbers the tool genuinely
produces today rather than restating the issue's aspirational figures.

## 0. Setup (before the room fills up)

1. Log in as the pre-provisioned demo organization:
   - Organization: `India Payments Platform`
   - Username: `india-payments-admin`
   - Password: the value of `ECDAT_DEMO_PASSWORD` (defaults to
     `SecureBank-Demo-2026` in the seeded demo environment)
2. Zip the sample project:
   ```bash
   cd sample_enterprise
   zip -r india-payments-platform.zip india-payments-platform
   ```

## 1. Upload and scan

Go to **Upload Center → Repository scan**, name the project
"India Payments Platform", set criticality to **Critical** (payments
infrastructure), and upload `india-payments-platform.zip`.

> "This is a synthetic codebase modeling six services in a typical Indian
> digital-payments stack — UPI, the NPCI gateway, Aadhaar-linked auth, legacy
> IMPS/NEFT settlement, a mobile banking API, and the core banking interface.
> Let's see what ECDAT-X finds."

**What to expect:** the scan discovers **54 cryptographic assets** across
**17 files** and **6 services** — real Python, Java, TypeScript, C, and
config-file code, not a mocked dataset.

## 2. Discovery results (Asset Explorer)

> "Found 54 crypto assets — a mix of algorithms, libraries, protocols, and a
> certificate reference — from something a presenter could scan live in front
> of you, not a pre-loaded dataset."

Point out the mix:
- **Algorithms**: RSA-2048, ECDSA (P-256), AES-256-GCM, SHA-256, SHA-1,
  HMAC, 3DES
- **Libraries**: Python `cryptography`, PyCryptodome, Bouncy Castle,
  Node.js `crypto`, OpenSSL
- **Protocols**: TLS 1.2 (three services)
- **Certificate**: an NPCI gateway TLS certificate reference

## 3. Risk dashboard

> "Not everything here is equally risky. ECDAT-X's six-factor risk engine
> ranks them."

**What to expect:** the top two findings are **RSA-2048** (UPI transaction
signing) and **ECDSA P-256** (NPCI gateway certificates) — both score **77/100,
"high" severity, "critical" quantum classification**. Both are broken by
Shor's algorithm on a cryptographically relevant quantum computer.

Point to the **IMPS/NEFT legacy service**: four separate lines of **3DES**
encryption in `LegacyCipher.java`, inherited from a 2009 core-banking rollout.
3DES is classically weak today (112-bit effective security) regardless of the
quantum timeline — this is the "should have been fixed years ago" finding
every legacy bank has somewhere.

## 4. Blast radius (Knowledge Graph / Blast Radius view)

> "If the UPI service's RSA-2048 signing key were compromised, what else
> breaks?"

Click into the RSA-2048 asset and open its blast radius graph. In this
demo's scan, RSA-2048 and AES-256 both live inside the UPI Payment Service,
so the graph shows that service as directly dependent.

**Honest caveat for this script**: a single repository scan produces one
application node per upload, so a same-org "N of 6 services affected"
statistic needs either separate scans per service or a hand-modeled
dependency graph (this is how the SecureBank demo achieves its blast-radius
numbers — see `backend/app/seed.py::seed_securebank_demo`). If you want that
specific narrative beat for India Payments Platform too, upload each
`services/*` subdirectory as its own project under the same organization
first — then a shared library (e.g. Bouncy Castle, used by both the NPCI
Gateway and any service you add later) will show real cross-service blast
radius.

## 5. Mosca inequality timeline (Quantum Risk Dashboard)

> "Banking records in India have long regulatory retention — RBI's KYC and
> transaction record rules run into years. Let's model that."

Open the Mosca section and set:
- **Data lifetime (X)**: 20 years (typical regulated financial record
  retention)
- **Migration time (Y)**: 3 years (a realistic estate-wide PQC migration)
- **Quantum arrival (Z)**: try the "Moderate" preset (2035)

**What to expect:** 20 + 3 = 23 years of required protection against a
9-year runway to 2035 → the timeline flags **CRITICAL — migration must begin
now**, exactly the inequality the research contribution is built on.

## 6. Migration roadmap

> "So what's the plan?"

Open **Migration Planner**. The 3DES entries in the IMPS/NEFT service and the
RSA-2048/ECDSA trust anchors get sequenced into early waves, with ML-KEM and
ML-DSA recommended as NIST-standardized replacements.

## 7. NQM compliance report

> "And because this is India, here's how it maps to the National Quantum
> Mission timeline."

Open **NQM Compliance** (industry is pre-set to "Fintech", which the tool
maps to the BFSI/RBI sector profile). Generate the PDF report from the
report menu — it shows phase-by-phase completion computed from this same
scan, plus RBI-specific guidance and a recommended ML-KEM-768/ML-DSA-65
baseline for customer-facing and settlement systems.

## Closing line

> "Every number in this walkthrough — the 54 assets, the 77/100 risk score,
> the Mosca verdict — came from a live scan you just watched, on a codebase
> that models exactly the kind of infrastructure this room cares about:
> UPI, NPCI, and Aadhaar."
