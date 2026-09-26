# PQC Candidate Benchmark, Maturity & Compatibility Research

**Scope:** All 18 hardcoded candidates in `migration_engine/pqc_knowledge_base.py` — ML-KEM-512/768/1024 (FIPS 203), ML-DSA-44/65/87 (FIPS 204), and the 12 SLH-DSA parameter sets (FIPS 205: SHA2/SHAKE × 128s/128f/192s/192f/256s/256f).

**Method:** Live web research (search + direct page/document fetch) conducted 2026-09-26. Sources checked: NIST CSRC (FIPS 203/204/205 final texts, Federal Register notice, PQC conference presentations), the Open Quantum Safe project (`openquantumsafe.org`, `github.com/open-quantum-safe/liboqs` README and docs), the **pqm4** project (`github.com/mupq/pqm4`, the standard academic ARM Cortex-M4 PQC benchmark suite, used because NIST's own FIPS documents do **not** publish cycle-count/latency tables — they are algorithm specifications, not performance reports), an independent 2026 arXiv benchmark paper on ARM Cortex-M0+ (RP2040), OpenSSL/wolfSSL/AWS-LC/BoringSSL release notes and issue trackers, and NVD/CVE search.

**Headline caveat that applies to every number below:** all cycle-count/latency figures come from **embedded microcontroller benchmarks** (ARM Cortex-M4 at 24 MHz via pqm4, and ARM Cortex-M0+ at 133 MHz via the RP2040 paper), not server/x86_64 hardware, and not from liboqs's own hosted dashboard (`openquantumsafe.org/benchmarking` is a JS-rendered visualization; it could not be scraped for numeric values via automated fetch — only its existence and methodology description could be confirmed). The pqm4/arXiv numbers are used here as the best available **cited, reproducible, cross-variant** dataset, and are reliable for **relative ordering within a family** (which variant is faster/slower than which), but should not be read as absolute production-hardware performance. This is exactly the kind of distinction the task requires making explicit.

---

## 1. ML-KEM (FIPS 203)

### Performance

Source: [arXiv:2603.19340](https://arxiv.org/html/2603.19340v5), "Benchmarking NIST-Standardised ML-KEM and ML-DSA on ARM Cortex-M0+" (Raspberry Pi Pico / RP2040, 133 MHz, PQClean reference C, `-Os`, 30 runs/op). Cross-checked for relative ordering against [pqm4 benchmarks.md](https://github.com/mupq/pqm4/blob/master/benchmarks.md) (Cortex-M4, 24 MHz).

| Variant | KeyGen | Encaps | Decaps | Full exchange | pqm4 cycles (keygen/encap/decap) |
|---|---|---|---|---|---|
| ML-KEM-512 | 9.94 ms (1,322 kc) | 11.53 ms | 14.23 ms | 35.71 ms (4,749 kc) | 595,793 / 700,605 / 888,653 |
| ML-KEM-768 | 16.02 ms (2,131 kc) | 18.58 ms | 22.02 ms | 56.62 ms (7,530 kc) | 988,722 / 1,138,225 / 1,387,984 |
| ML-KEM-1024 | 25.18 ms (3,349 kc) | 28.10 ms | 32.45 ms | 85.73 ms (11,402 kc) | 1,536,343 / 1,708,071 / 2,020,327 |

Both independent datasets agree: ML-KEM-512 is fastest, 768 is ~1.6× slower, 1024 is ~2.4× slower than 512, monotonically across every operation. This **confirms** the existing ordinal `performance_rank` (512=3 fastest, 768=2, 1024=1 slowest).

Parameter sizes in the code (800/768, 1184/1088, 1568/1568 bytes) match FIPS 203 Table 2 exactly — not in question.

### Maturity

- FIPS 203 finalized and published **2024-08-13**, effective 2024-08-14 ([Federal Register notice](https://www.federalregister.gov/documents/2024/08/14/2024-17956/announcing-issuance-of-federal-information-processing-standards-fips-fips-203-module-lattice-based)).
- liboqs classifies ML-KEM as its highest support tier ("Core"/Tier 1) per the [liboqs README](https://github.com/open-quantum-safe/liboqs/blob/main/README.md), and has carried Kyber/ML-KEM since well before FIPS finalization.
- **CVE-2024-37880**: the pre-standardization Kyber reference implementation had a Clang-compiler-induced timing side channel (`poly_frommsg`) that let an attacker recover an ML-KEM-512 secret key in minutes when built with certain optimization flags. Found by Antoon Purnal (PQShield); fixed upstream before/around FIPS finalization. This is a **real, cited implementation-level side-channel finding**, not a design flaw in ML-KEM itself, but it is a legitimate maturity signal (early implementations were fragile to compiler-introduced leaks).
- Separately, **CVE-2024-31510** is filed against `liboqs` v0.10.0's AVX2 implementation of `ML-DSA-44-ipd` (initial public draft) — i.e. a pre-final ML-DSA build, not ML-KEM; noted here and repeated under ML-DSA below to avoid confusion between the two families.

### Compatibility

- **OpenSSL 3.5.0** (released 2025-04-08, LTS to 2030): native provider support for ML-KEM; the release changed the **default** TLS supported-groups list to prefer hybrid PQC, with `X25519MLKEM768` as a default keyshare ([OpenSSL 3.5 release notes](https://openssl-library.org/news/openssl-3.5-notes/)).
- **BoringSSL**: ML-KEM supported since 2024 and used by Chrome for TLS (widely reported; Google's own PQC blog/changelog, corroborated by multiple secondary sources).
- **AWS-LC**: supports ML-KEM (confirmed in [aws/aws-lc#3305](https://github.com/aws/aws-lc/issues/3305), which states "AWS-LC supports ML-KEM (FIPS 203) and ML-DSA (FIPS 204) but not SLH-DSA (FIPS 205)").
- **wolfSSL**: announced "full implementation and support for ML-KEM and ML-DSA" 2024-10-01 ([wolfSSL blog](https://www.wolfssl.com/support-for-the-official-post-quantum-standards-ml-kem-and-ml-dsa/)).

### Recommended scores

| | ML-KEM-512 | ML-KEM-768 | ML-KEM-1024 |
|---|---|---|---|
| performance_rank | 3 (fastest) — **confirmed** | 2 — **confirmed** | 1 (slowest) — **confirmed** |
| maturity | Real evidence supports "mature but with a documented historical implementation CVE"; **cannot justify a bare 1.0** — recommend ~0.9, cite CVE-2024-37880, or keep "expert-estimated" if the team wants to avoid subjective docking | same | same |
| compatibility | Supported by OpenSSL 3.5, BoringSSL, AWS-LC, wolfSSL — broadest ecosystem support of any of the 18 candidates. Insufficient granular data to justify *0.85 vs 0.90 vs 0.80* specifically (no source ranks the three parameter sets differently in library support — all three ship together in every library found) — recommend a single **equal** compatibility value across all three ML-KEM sizes, flagged below | same evidence, same caveat | same evidence, same caveat |
| migration_complexity | No cited source speaks to migration effort/complexity at all — **insufficient public data; recommend expert-estimated placeholder** | same | same |

---

## 2. ML-DSA (FIPS 204)

### Performance

Source: same arXiv:2603.19340 paper (Cortex-M0+), cross-checked against pqm4 (Cortex-M4).

| Variant | KeyGen | Sign (mean) | Verify | pqm4 cycles (keygen/sign/verify) |
|---|---|---|---|---|
| ML-DSA-44 | 39.8 ms (5,297 kc) | 158.9 ms (high variance, CV 67.5%; p99 = 489.9 ms) | 44.0 ms | 1,874,405 / 7,925,955 / 2,063,096 |
| ML-DSA-65 | 68.4 ms (9,100 kc) | 256.6 ms (CV 73.1%; p99 = 953.6 ms) | 72.2 ms | 3,205,533 / 12,359,056 / 3,377,305 |
| ML-DSA-87 | 114.3 ms (15,201 kc) | 355.2 ms (p99 = 1,125.0 ms) | 120.2 ms | 5,341,863 / 15,579,513 / 5,610,203 |

Both datasets agree ML-DSA-44 is fastest, 65 middle, 87 slowest, **confirming** the existing `performance_rank` (44=3, 65=2, 87=1). The paper separately notes that ML-DSA's rejection-sampling loop gives sign latency a very high coefficient of variation (66–73%) with worst-case p99 sign times over 1 second at the 87 level on constrained hardware — a real, cited caveat about *tail* latency that a single scalar `performance_rank` cannot capture, but which is directly relevant to any risk model driven by these scores.

Parameter sizes (1312/2420, 1952/3309, 2592/4627 bytes) match FIPS 204 exactly.

### Maturity

- FIPS 204 finalized 2024-08-13 (same Federal Register notice as above).
- liboqs support tier: "Supported"/Tier 2 per liboqs README — one notch below ML-KEM's top tier.
- **CVE-2024-31510**: liboqs v0.10.0's AVX2 implementation of `pqcrystals-dilithium-standard_ml-dsa-44-ipd` (the *initial public draft*, pre-final parameter set naming) had a signature-verification-related vulnerability. This is against a **pre-final draft build**, so it is not evidence against the FIPS-final ML-DSA-44, but it is a legitimate "early implementation fragility" data point worth citing, exactly as the task's CVE-search requirement asks for.
- Broader academic literature (fault-injection and side-channel papers against Dilithium/ML-DSA, e.g. IACR ePrint 2024/238 "A Single Trace Fault Injection Attack on Hedged CRYSTALS-Dilithium") shows active, ongoing side-channel research against ML-DSA implementations — normal for a 2-year-old standard, but a real signal that "maturity" should not be treated as maxed-out just because the algorithm is FIPS-final.

### Compatibility

- OpenSSL 3.5.0: native provider support (same release note as ML-KEM).
- wolfSSL: "full implementation and support for ML-KEM and ML-DSA" (2024-10-01, same source as above).
- AWS-LC: confirmed support via aws-lc#3305.
- AWS KMS added ML-DSA support 2025-06 per AWS's own "what's new" post (found in search results; not independently fetched in full, cited with appropriate caution).

### Recommended scores

Same structure as ML-KEM: performance_rank ordering is **confirmed** by two independent cited benchmark sources. Maturity/compatibility/migration_complexity numeric *scalars* (as opposed to ordering) are **not independently justified by any source found** — recommend either "expert-estimated, no data available" labels, or at minimum footnoting that the current 1.0/0.85–0.90 values are plausible directionally (ML-DSA-65 does appear to be the most broadly supported "sweet spot" level across the libraries checked, matching its highest compatibility=0.90) but are not derived from a citable metric.

---

## 3. SLH-DSA (FIPS 205) — all 12 parameter sets

### Performance

Source: [pqm4 benchmarks.md](https://github.com/mupq/pqm4/blob/master/benchmarks.md) (ARM Cortex-M4, 24 MHz, arm-none-eabi-gcc 11.3, min/max/avg of 100 runs). This is the only source found that gives cycle-accurate, cross-variant, citable numbers for all 12 SLH-DSA parameter sets simultaneously.

| Variant | KeyGen (cycles) | Sign (cycles) | Verify (cycles) |
|---|---|---|---|
| SLH-DSA-SHA2-128f | 15,742,990 | 368,575,228 | 21,923,628 |
| SLH-DSA-SHA2-128s | 1,007,731,522 | 7,657,558,168 | 7,471,794 |
| SLH-DSA-SHA2-192f | 23,570,224 | 666,398,438 | 35,457,937 |
| SLH-DSA-SHA2-192s | 1,509,654,951 | 15,452,089,990 | 13,494,855 |
| SLH-DSA-SHA2-256f | 62,583,556 | 1,377,768,608 | 37,302,611 |
| SLH-DSA-SHA2-256s | 1,001,040,810 | 14,326,202,444 | 19,637,153 |
| SLH-DSA-SHAKE-128f | 50,505,025 | 1,182,422,563 | 70,501,834 |
| SLH-DSA-SHAKE-128s | 3,231,401,965 | 24,553,696,412 | 24,366,771 |
| SLH-DSA-SHAKE-192f | 74,890,591 | 1,937,690,056 | 103,305,801 |
| SLH-DSA-SHAKE-192s | 4,793,551,013 | 43,114,327,277 | 35,026,412 |
| SLH-DSA-SHAKE-256f | 200,110,912 | 4,026,533,198 | 108,394,619 |
| SLH-DSA-SHAKE-256s | 3,201,898,694 | 38,175,697,620 | 52,912,174 |

**Findings directly relevant to the hardcoded `performance_rank` values:**

1. The "f" (fast) variants sign ~10–40× faster than the "s" (small) variants at the same level, but "s" variants verify ~2–3× faster than "f" — this matches the code's own `notes` field ("Small signature, slower" / "Fast signature, larger") and is now backed by a citable number.
2. **SHAKE variants are consistently 2.5–3.5× slower than SHA2 variants at every matched parameter set** (e.g. SHA2-128f sign = 368.6M cycles vs SHAKE-128f sign = 1.18B cycles — 3.2× slower; SHA2-256s = 14.33B vs SHAKE-256s = 38.18B — 2.7× slower). **The current code assigns identical `performance_rank` values to the SHA2 and SHAKE variant of each level/speed combination** (the loop in `pqc_knowledge_base.py` reuses the same `pr` for both `variant in ["SHA2","SHAKE"]`). This is **contradicted by real benchmark evidence** — SHA2 variants should rank strictly faster than their SHAKE counterparts, not tie.
3. Within the "s" family, the code ties `192s` and `256s` at `performance_rank=1` for both levels 3 and 5. The SHA2 data shows `256s` (14.33B cycles) is actually marginally *faster* to sign than `192s` (15.45B cycles) — a small but real inversion versus a naive "higher security level = slower" assumption. Minor, but it is evidence against treating the tie as self-evidently correct.
4. **The most consequential finding for the TOPSIS engine**: `performance_rank` is scaled 1–3 for ML-DSA and 1–5 for SLH-DSA, assigned independently per family, but both families feed the same `digital_signature` candidate pool consumed by `topsis_engine.py`. In absolute terms, even the fastest SLH-DSA variant (SHA2-128f, 368.6M sign-cycles) is **~46× slower to sign** than the slowest ML-DSA variant (ML-DSA-87, 15.6M cycles), and the slowest SLH-DSA variant (SHAKE-192s, 43.1B cycles) is **~2,700× slower** than ML-DSA-44. Yet SLH-DSA-SHA2-128f carries `performance_rank=5`, numerically *higher* than any ML-DSA candidate (max 3). If TOPSIS treats `performance_rank` as a directly comparable "higher is better" criterion across the whole `digital_signature` candidate set (as the field's own docstring — "higher is better/faster" — implies it should), **SLH-DSA candidates will be scored as faster than ML-DSA candidates that are 1–2 orders of magnitude faster in reality.** This is a real, evidence-backed defect worth flagging to the engineering team regardless of the specific 0–1 scores chosen.

### Maturity

- FIPS 205 finalized 2024-08-13, same Federal Register notice as FIPS 203/204.
- liboqs support tier: **"Community"/Tier 3** — one tier below ML-DSA and two below ML-KEM per the liboqs README's own tiering language. This is a **direct, citable contradiction** of the hardcoded `maturity=1.0` applied uniformly to all 12 SLH-DSA candidates (same value as ML-KEM/ML-DSA) — liboqs itself does not treat SLH-DSA as equally mature/production-ready.
- No SLH-DSA-specific CVE was found in NVD/CVE search. What was found instead is academic side-channel research: "Side Channel Resistant SPHINCS+" (NIST PQC 2024 conference paper, [csrc.nist.gov](https://csrc.nist.gov/csrc/media/Presentations/2024/side-channel-resistant-sphincs-plus/images-media/fluhrer_side-channel-pqc2024.pdf)) documents that naive SLH-DSA implementations leak the `SK.seed` master key rapidly under power/timing analysis unless specifically hardened, and a 2025 paper "SLasH-DSA: Breaking SLH-DSA Using an Extensible End-to-End Rowhammer Framework" ([arXiv:2509.13048](https://arxiv.org/pdf/2509.13048)) demonstrates a hardware-fault-based break of SLH-DSA implementations. Neither is a formally assigned CVE, but both are legitimate, citable, recent (2024–2025) implementation-security findings against SLH-DSA specifically that have no ML-KEM/ML-DSA equivalent found in this research pass.

### Compatibility

- **AWS-LC does not support SLH-DSA** as of the still-open request thread [aws/aws-lc#3305](https://github.com/aws/aws-lc/issues/3305) (opened 2026-06-18): "AWS-LC supports ML-KEM (FIPS 203) and ML-DSA (FIPS 204) but not SLH-DSA (FIPS 205)," with the maintainers undecided on which of the 12 parameter sets they would even pick to support.
- **wolfSSL's own October 2024 announcement**, which trumpets ML-KEM/ML-DSA support, explicitly does **not** claim SLH-DSA support and instead asks interested parties to contact wolfSSL sales — i.e., as of that announcement SLH-DSA was not yet a shipped feature (current 2026 status not independently re-verified in this pass; flagged as a gap).
- **BoringSSL**: no SLH-DSA support found in this research pass (only ML-KEM confirmed).
- **OpenSSL 3.5.0** does list SLH-DSA in its top-level "Support for PQC algorithms (ML-KEM, ML-DSA and SLH-DSA)" release note, so OpenSSL is currently the most concrete library-level SLH-DSA support found.

This is a real, multi-source-confirmed basis for SLH-DSA's compatibility score being lower than ML-KEM/ML-DSA — which the existing hardcoded value (`compatibility=0.60` for all 12 SLH-DSA candidates, vs 0.80–0.90 for ML-KEM/ML-DSA) already reflects directionally. What is **not** justified by any source found is a specific number like 0.60 versus, say, 0.50 or 0.70 — no source quantifies "compatibility" as a scalar.

### Recommended scores (all 12 variants)

- **performance_rank**: real cycle data exists (table above) and can be used to derive a properly ordered rank across all 12 variants (and, if the team fixes the cross-family scaling issue in finding #4 above, across all 15 `digital_signature` candidates together). Recommend recomputing ranks from the pqm4 sign-cycle column rather than hand-assigning.
- **maturity**: insufficient public data to justify any specific scalar (e.g. 0.7 vs 0.8); however, there is clear cited evidence that it should be **lower than ML-KEM/ML-DSA's maturity value**, contradicting the current uniform 1.0. Recommend "expert-estimated, no data available" for the precise number, but flag the uniform-1.0 assumption as contradicted.
- **compatibility**: same — direction (lower than ML-KEM/ML-DSA) is evidence-backed; exact scalar is not. "Expert-estimated" recommended for the number itself.
- **migration_complexity**: no source found addresses this for any candidate, SLH-DSA included. "Insufficient public data; recommend expert-estimated placeholder" for all 12.

---

## 4. Comparison against current hardcoded values

All 18 current values were read directly from `migration_engine/pqc_knowledge_base.py` (provided in full below since the code was available for direct inspection — there was no gap to flag on "which values exist," only on "are they justified").

| Candidate | performance_rank | maturity | compatibility | migration_complexity | Verdict |
|---|---|---|---|---|---|
| ML-KEM-512 | 3 | 1.0 | 0.85 | 0.8 | Rank **confirmed** by 2 independent cited benchmarks. Maturity=1.0 **contradicted** (CVE-2024-37880 exists against early implementations); compatibility/migration_complexity **no evidence either way** for the specific scalar (though broad multi-library support is confirmed qualitatively). |
| ML-KEM-768 | 2 | 1.0 | 0.90 | 0.7 | Rank **confirmed**. Maturity=1.0 same caveat as above. Compatibility/migration_complexity: **no evidence for the scalar**, though no source differentiates 768 from 512/1024 in library support (all three ship together everywhere checked) — the *relative* 0.90>0.85>0.80 gradient across the three ML-KEM sizes has **no supporting citation**. |
| ML-KEM-1024 | 1 | 1.0 | 0.80 | 0.6 | Rank **confirmed**. Same maturity caveat. Compatibility=0.80 (lowest of the three) has **no citation** — all libraries found support all three sizes identically. |
| ML-DSA-44 | 3 | 1.0 | 0.85 | 0.7 | Rank **confirmed** by 2 sources. Maturity=1.0 **weakly contradicted** (CVE-2024-31510 against a pre-final draft build, plus ongoing fault-injection research) — not a strong contradiction since the CVE is against IPD, not final ML-DSA. Compatibility/migration_complexity: **no evidence for scalar**. |
| ML-DSA-65 | 2 | 1.0 | 0.90 | 0.6 | Rank **confirmed**. Same maturity note. Compatibility=0.90 (highest of the three ML-DSA sizes) is **plausible but uncited** — no source ranks the three ML-DSA sizes differently for support. |
| ML-DSA-87 | 1 | 1.0 | 0.80 | 0.5 | Rank **confirmed**. Same notes as above. |
| SLH-DSA-*-128s (×2) | 2 | 1.0 | 0.60 | 0.4 | Performance rank ordering **directionally plausible but not verified against SHA2/SHAKE distinction** (see finding #2) — the same rank is applied to both SHA2-128s and SHAKE-128s despite SHAKE being ~3× slower. Maturity=1.0 **contradicted** by liboqs's own "Community" tier classification. Compatibility=0.60 direction **confirmed** (lower than ML-KEM/ML-DSA, per AWS-LC non-support and wolfSSL's 2024 non-support) but exact scalar uncited. |
| SLH-DSA-*-128f (×2) | 5 | 1.0 | 0.60 | 0.4 | Same SHA2/SHAKE tying issue — **contradicted**, SHA2-128f is ~3.2× faster than SHAKE-128f per pqm4 but both get rank 5. Also, this is the single most severe instance of finding #4: rank 5 exceeds every ML-DSA rank (max 3) despite being 46–2700× slower in absolute cycles. Maturity/compatibility notes same as above. |
| SLH-DSA-*-192s (×2) | 1 | 1.0 | 0.60 | 0.4 | Tied with 256s at rank 1; SHA2 data shows 256s is marginally *faster* to sign than 192s (finding #3) — **mild contradiction** of the implicit "higher level = slower, tie is fine" assumption. SHA2/SHAKE tying issue applies here too. |
| SLH-DSA-*-192f (×2) | 4 | 1.0 | 0.60 | 0.4 | SHA2/SHAKE tying issue applies (192f SHAKE is ~2.9× slower than SHA2 per pqm4 but same rank). |
| SLH-DSA-*-256s (×2) | 1 | 1.0 | 0.60 | 0.4 | See 192s note — tie with 192s not clearly correct per SHA2 data. SHA2/SHAKE tying issue applies. |
| SLH-DSA-*-256f (×2) | 3 | 1.0 | 0.60 | 0.4 | SHA2/SHAKE tying issue applies (256f SHAKE ~2.9× slower than SHA2 per pqm4, same rank). |

**Summary verdicts:**
- **Confirmed by evidence**: all 6 ML-KEM/ML-DSA `performance_rank` orderings (relative, not absolute); the qualitative direction of SLH-DSA's lower `compatibility` and (implicitly) lower `maturity` relative to ML-KEM/ML-DSA.
- **Contradicted by evidence**: uniform `maturity=1.0` across all 18 candidates (SLH-DSA is liboqs "Community" tier, not top tier; ML-KEM/ML-DSA have documented early-implementation CVEs); the SHA2/SHAKE `performance_rank` tie within each SLH-DSA level/speed combination (real ~2.5–3.5× cycle-count gap exists); the 192s/256s `performance_rank` tie (SHA2 data shows a small but real inversion); and, most importantly, the cross-family comparability of `performance_rank` between ML-DSA (scale 1–3) and SLH-DSA (scale 1–5) feeding the same TOPSIS `digital_signature` pool, which inverts the true 46–2700× real-world performance gap.
- **No evidence either way (gap)**: every specific `compatibility` and `migration_complexity` *scalar* value (0.85 vs 0.90 vs 0.80, 0.4 vs 0.5 vs 0.6 vs 0.7 vs 0.8, etc.) across all 18 candidates. No source found quantifies "compatibility" or "migration complexity" as a number for any PQC candidate — every citation found supports only qualitative/binary statements ("library X supports algorithm Y" or "library X does not"). These fields should be labeled "expert-estimated, no data available" rather than presented as measured.

---

## Sources cited

- NIST, [FIPS 203 final](https://csrc.nist.gov/pubs/fips/203/final), [FIPS 204 final](https://csrc.nist.gov/pubs/fips/204/final), FIPS 205 final (csrc.nist.gov/pubs/fips/205/final)
- [Federal Register, 2024-08-14 issuance notice for FIPS 203/204/205](https://www.federalregister.gov/documents/2024/08/14/2024-17956/announcing-issuance-of-federal-information-processing-standards-fips-fips-203-module-lattice-based)
- [Open Quantum Safe — liboqs README](https://github.com/open-quantum-safe/liboqs/blob/main/README.md) and [openquantumsafe.org/benchmarking](https://openquantumsafe.org/benchmarking) (methodology/tiering confirmed; live numeric dashboard not scrapeable via automated fetch)
- [pqm4 project](https://github.com/mupq/pqm4) — [benchmarks.md](https://github.com/mupq/pqm4/blob/master/benchmarks.md), the source of the full 12-variant SLH-DSA cycle table and the ML-KEM/ML-DSA cross-check table
- [arXiv:2603.19340 — "Benchmarking NIST-Standardised ML-KEM and ML-DSA on ARM Cortex-M0+"](https://arxiv.org/html/2603.19340v5)
- [OpenSSL 3.5 release notes](https://openssl-library.org/news/openssl-3.5-notes/)
- [wolfSSL — "Support for the Official Post-Quantum Standards ML-KEM and ML-DSA"](https://www.wolfssl.com/support-for-the-official-post-quantum-standards-ml-kem-and-ml-dsa/) (2024-10-01)
- [aws/aws-lc issue #3305 — "SLH-DSA Support"](https://github.com/aws/aws-lc/issues/3305)
- CVE-2024-37880 (Kyber/ML-KEM reference implementation timing side channel, NVD/OSV)
- CVE-2024-31510 (liboqs v0.10.0 ML-DSA-44-ipd AVX2 implementation)
- NIST PQC 2024 conference paper: [Fluhrer, "Side Channel Resistant SPHINCS+"](https://csrc.nist.gov/csrc/media/Presentations/2024/side-channel-resistant-sphincs-plus/images-media/fluhrer_side-channel-pqc2024.pdf)
- [arXiv:2509.13048 — "SLasH-DSA: Breaking SLH-DSA Using an Extensible End-to-End Rowhammer Framework"](https://arxiv.org/pdf/2509.13048)
- IACR ePrint 2024/238 — "A Single Trace Fault Injection Attack on Hedged CRYSTALS-Dilithium"

## Known gaps in this research

- Could not retrieve numeric data directly from `openquantumsafe.org/benchmarking`'s own dashboard (JavaScript-rendered; only its existence, purpose, and tiering language were confirmed via text extraction).
- Could not independently re-verify wolfSSL's *current* (2026) SLH-DSA support status beyond the October 2024 announcement, which predates SLH-DSA support in that library, if any was added since.
- x86_64/server-class latency numbers (as opposed to ARM Cortex-M0+/M4 embedded numbers) were not found in a citable, structured, cross-variant form; liboqs's own `speed_kem`/`speed_sig` tool output exists but is not published as static server-hardware tables anywhere this research could reach — only the tool's existence and usage were confirmed.
- No CVE was found specifically against a FIPS-final SLH-DSA implementation (as opposed to academic side-channel/fault papers) — this is reported as an absence of evidence, not evidence of absence.
