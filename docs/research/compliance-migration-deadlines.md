# Compliance & Regulatory PQC Migration Deadlines — Research Findings

**Research date:** 2026-09-26
**Scope:** This document catalogs real, published, dated regulatory/compliance guidance
relevant to post-quantum cryptography (PQC) migration, across the seven regimes requested
for ECDAT-X's migration-prioritization roadmap. It is sourced research only — no code,
schema, or scoring logic is proposed here. All dates and quotes below are attributed to a
specific published source; where a claim could not be confirmed against a primary source it
is marked as such.

**Method:** Web search plus direct fetch of primary-source pages/PDFs (NSA/media.defense.gov,
NCSC, ANSSI/cyber.gouv.fr, BSI, DST, NIST) conducted on 2026-09-26. Several PDFs (NSA CNSA 2.0
algorithm annex, ETSI TR 103 619, the Indian DST Task Force PDF) could not be fully text-extracted
by the fetch tooling used (403 blocks or binary/PDF decode failures); for those, findings are
corroborated via secondary sources that quote the primary documents directly, and this is noted
per-section. Anyone implementing against these findings should re-verify against the primary PDF
before encoding a hard deadline into scoring logic.

**Existing repo context:** `config/nqm_compliance.json` already encodes a 3-phase India-NQM-aligned
migration timeline (2024-2026 inventory, 2026-2029 CII migration, 2029-2033 enterprise-wide), and
its own `source` field self-discloses: *"Illustrative alignment with India's National Quantum
Mission (NQM) and the DST post-quantum migration roadmap. Not an official government compliance
framework."* Section 5 below compares this against what has since actually been published.

---

## 1. US NSA CNSA 2.0 (Commercial National Security Algorithm Suite 2.0)

**Documents:**
- *CNSA 2.0 and Quantum Computing FAQ* ("CSI: Commercial National Security Algorithm Suite 2.0 FAQ"), NSA, originally published September 2022, updated **December 2024 (Version 2.1)**. Hosted at nsa.gov Press Room / Digital Media Center (media.defense.gov/2022/Sep/07/2003071836/-1/1/1/CSI_CNSA_2.0_FAQ_.PDF).
- *CNSA 2.0 Algorithms* advisory, NSA, PP-22-1338, dated Sept 2022 / republished May 2025 (media.defense.gov/2025/May/30/2003728741/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS.PDF). Direct fetch of this PDF returned HTTP 403 during this research session; timeline details below are corroborated via secondary sources (Encryption Consulting, PostQuantum.com, QuantumSequrity) that reproduce the NSA table.

**What it mandates (by system category, "support and prefer" → "exclusive use" dates):**
- **Software and firmware signing:** support/prefer CNSA 2.0 by **2025**; exclusive use by **2030**. Algorithms: LMS or XMSS per NIST SP 800-208 (hash-based signatures), chosen because signed code/updates are especially exposed to harvest-now-decrypt-later risk.
- **Web browsers, servers, and cloud services:** support/prefer by **2025**; exclusive use by **2033**.
- **Traditional networking equipment (VPN, routing):** support/prefer by **2026**; exclusive use by **2030**.
- **Operating systems:** support/prefer by **2027**; exclusive use by **2033**.
- **Constrained devices / large PKI systems:** support/prefer by **2030**; exclusive use by **2033**.
- **Custom applications and legacy systems:** must be updated or replaced entirely by **2033**.
- **Acquisition gate:** from **January 1, 2027**, new National Security System (NSS) equipment acquisitions are expected to be CNSA 2.0–compliant by default.
- **Core mandated algorithms across categories:** ML-KEM-1024 (key establishment) and ML-DSA-87 (general-purpose signatures) at all classification levels; LMS/XMSS specifically for firmware/software signing.
- This sits inside the broader **National Security Memorandum 10 (NSM-10)** goal of full quantum-resistance across NSS by **2035**; NSA states it expects most equipment categories to be ahead of that broader deadline.

**Scope:** National Security Systems (NSS) — i.e., US government/defense classified and mission systems, and the vendors/contractors supplying them (defense industrial base). It is **not** a general-industry mandate, though CNSA 2.0 compliance is increasingly referenced as a de facto benchmark by contractors seeking NIAP/FIPS 140-3 certification.

**Confidence:** Binding for NSS and covered contractors (issued as a National Security Agency Cybersecurity Advisory under NSM-10 authority). Not a legal mandate for commercial/civilian industry outside that supply chain.

---

## 2. Germany BSI (TR-02102 series)

**Document:** BSI Technical Guideline **TR-02102-1**, *"Cryptographic Mechanisms: Recommendations and Key Lengths,"* **Version 2026-01** (published 23 January 2026) — bsi.bund.de. Companion document: *"Migration zu Post-Quanten-Kryptografie – Handlungsempfehlungen des BSI"* (PDF, bsi.bund.de).

**What it mandates/recommends:**
- Raised the general minimum security-level requirement to **120 bits**.
- Recommended PQC KEMs: **FrodoKEM, Classic McEliece, ML-KEM**.
- Recommended PQC signature schemes: **ML-DSA, SLH-DSA**, plus stateful hash-based schemes **LMS/HSS and XMSS/XMSS-MT**.
- Explicit sunset date: BSI recommends sole reliance on **classical-only key-agreement mechanisms only until 31 December 2031** — after that, hybrid or PQC-only key agreement is expected.
- For systems with **very high protection requirements**, the transition to quantum-safe mechanisms should be **completed by 31 December 2030**.
- References the wider **European roadmap** calling for migration to quantum-safe **signature** mechanisms by **2035 at the latest**.
- BSI continues to recommend **hybrid** (classical + PQC combined) deployments as the default approach, not PQC-only, for most use cases at present.

**Scope:** TR-02102 is a technical guideline written primarily for German federal government IT systems and vendors seeking BSI approval, but it is very widely used across German and EU industry (finance, critical infrastructure) as a de facto cryptographic standard, well beyond strict government mandate.

**Confidence:** Official technical recommendation from a national cybersecurity authority — binding for German federal government systems and BSI-certified products; treated as strong (but not legally binding) best-practice guidance for private industry.

---

## 3. EU ETSI (quantum-safe cryptography technical reports/standards)

**Documents found (chronological):**
- ETSI **TR 103 619 V1.1.1** (2020-07), *"CYBER; Migration strategies and recommendations to Quantum Safe schemes"* — direct PDF fetch failed (binary/undecoded content); confirmed via ETSI's own 2020-08 press release ("ETSI releases migration strategies and recommendations for Quantum-Safe schemes").
- ETSI **TR 103 949 V1.1.1** (2023-05), *"Quantum-Safe Cryptography (QSC) Migration"* (etsi.org/deliver).
- ETSI **TR 104 016 V1.1.1** (2024-10), *"A Repeatable Framework for Quantum-Safe Migrations."*
- ETSI **TS 103 744 V1.2.1** (2025-03), *"Quantum-Safe Hybrid Key Establishment."*

**What it recommends:** ETSI's migration guidance is framed as a generic **three-stage process** rather than fixed calendar dates:
1. **Inventory compilation** — identify assets/processes affected by quantum risk.
2. **Migration planning** — decide whether/when each asset moves to a "Fully Quantum-Safe Cryptographic State" (FQSCS).
3. **Execution** — carry out and manage the migration.

No ETSI document found in this research gives a specific calendar deadline (e.g., "by 2030") — the guidance is process/methodology-oriented, stating only that migration efforts should begin now rather than be deferred.

**Scope:** ETSI standards apply voluntarily across European (and internationally adopting) telecom and IT industry members; ETSI is a standards body, not a regulator, so its documents are not legally binding on anyone. They are frequently referenced by national regulators (e.g., BSI, ANSSI) as supporting methodology.

**Confidence:** Informal/voluntary technical guidance — not a regulatory mandate. Useful as a methodology reference, not a source of hard deadlines.

---

## 4. France ANSSI

**Document:** *"ANSSI views on the Post-Quantum Cryptography transition"* (English translation), ANSSI, first published **4 January 2022**, with a follow-up FAQ (*"FaQ sur la Cryptographie post-quantique"*) at cyber.gouv.fr, and later reaffirmations (e.g., the 2024 G7 joint call to action, and a 2025/2026 "premiers visas de sécurité incluant de la cryptographie post-quantique" update noting ANSSI has begun issuing security certifications ("visas") that include PQC).

**What it recommends:**
- A **three-phase roadmap**:
  - **Phase 1 (from 2022):** optional PQC, hybrid mechanisms only, for defense-in-depth alongside classical crypto.
  - **Phase 2 ("not before 2025"):** hybrid mechanisms become **mandatory**, with a component offering claimed quantum resistance, pending finalization of NIST's first PQC standards.
  - **Phase 3 ("probably not before 2030"):** standalone (non-hybrid) post-quantum cryptography becomes an accepted option.
- Algorithm guidance for early deployments: candidates should be NIST finalists or well-studied trusted alternates — ANSSI names **FrodoKEM, Kyber (now ML-KEM), Dilithium (now ML-DSA), or Falcon** as reasonable Phase-1 choices, generally at **NIST security level V** (≈AES-256-equivalent).
- Hash-based signatures are exempted from the hybridization requirement due to mature security proofs.
- ANSSI has separately signaled that it **"will not be reasonable to purchase products that do not integrate PQC after 2030,"** effectively a procurement-driven deadline.

**Scope:** Explicitly aimed at **industry broadly** — ANSSI states the guidance is meant to "provide directions to industrials developing security products," and applies to any vendor/organization seeking ANSSI security certification ("visa"), not government systems alone.

**Confidence:** Official national guidance/position paper from France's cybersecurity agency — not itself a binding law, but it directly gates ANSSI product certifications (visas), which are often required for use in French government and regulated-sector procurement, giving it real regulatory teeth in that channel.

---

## 5. India — National Quantum Mission (NQM) / DST Task Force

**Document:** *"Implementation of Quantum Safe Ecosystem in India — Report of the Task Force,"* Department of Science and Technology (DST), released **5 February 2026** (public comment period through **19 February 2026**), produced by a Task Force on PQC migration constituted under the **National Quantum Mission (NQM)**. PDF: dst.gov.in/sites/default/files/Report_TaskForce_PQMigration_4Feb26(v1).pdf (direct text extraction failed in this session — binary PDF decode issue; findings below corroborated via two independent secondary sources, PostQuantum.com and ORF, both of which quote the report directly and agree with each other on dates).

**What it recommends — migration timeline, split by sector tier:**
- **Critical Information Infrastructure (CII)** — defence, telecom, power, ISRO/DRDO/ONGC ("Urgent Adopters"):
  - **2027:** Build foundations — governance, cryptographic inventory, pilots, CBOM (Cryptographic Bill of Materials) requirements begin.
  - **2028:** Migrate high-priority systems.
  - **2029:** Full PQC adoption across CII.
- **General enterprises (government & private)** — banking, healthcare, education, e-governance, insurance ("Regular Adopters"), plus technology providers/enablers (HSM vendors, PKI providers, cloud platforms, crypto libraries, network OEMs):
  - **2028:** Build foundations.
  - **2030:** Migrate high-priority systems.
  - **2033:** Full PQC adoption.
- **CBOM (Cryptographic Bill of Materials) submissions become mandatory starting FY 2027–28** (i.e., from April 2027) — this is the single nearest-term concrete compliance obligation found for India.
- A national quantum-safe product-category list is planned, modeled on a **CISA January 2026 product-category advisory**, with India-specific additions (mobile phones; automated cryptographic discovery/inventory tools).
- Sub-Group 1 (led by TEC) is separately drafting a certification framework: *"Draft Framework for Testing and Certification of PQC-based Products and Solutions."*

**Scope:** Government-endorsed national roadmap covering both CII (mandatory-leaning, tighter timeline) and general enterprise/government sectors (looser timeline). It is a Task Force report commissioned under a government mission (NQM/DST), not yet a codified law or a CERT-In binding advisory — no CERT-In-specific PQC advisory was found in this research.

**Confidence:** Official government task-force roadmap — a strong policy signal and the likely basis for future binding rules (especially the CBOM mandate, which reads as closer to a firm regulatory requirement given its FY-specific date), but as of the research date it is a **published recommendation/roadmap**, not yet enacted binding law. Note this is materially different from — and more specific/recent than — the illustrative timeline (2024-2026 / 2026-2029 / 2029-2033) currently hardcoded in `config/nqm_compliance.json`, which predates this report and should be revisited: the real DST roadmap splits CII (2027/2028/2029) from general enterprise (2028/2030/2033) rather than using one unified timeline, and adds the concrete FY2027-28 CBOM deadline that the current config does not encode at all.

---

## 6. UK NCSC

**Document:** *"Timelines for migration to post-quantum cryptography,"* National Cyber Security Centre (NCSC), published **20 March 2025**, at ncsc.gov.uk/guidance/pqc-migration-timelines.

**What it mandates/recommends — three concrete milestone dates:**
- **By 2028:** "Define your migration goals," "carry out a full discovery exercise," "build an initial plan for migration" — i.e., complete inventory of cryptography-dependent systems/services and produce an estate-wide migration plan.
- **By 2031:** "Carry out your early, highest-priority PQC migration activities," "refine your plan so that you have a thorough roadmap for completing migration" — highest-priority systems migrated, plan refined.
- **By 2035:** "Complete migration to PQC of all your systems, services and products" — full transition for everything.

**Scope:** Explicitly targeted at "technical decision-makers and risk owners of **large organisations**, **operators of critical national infrastructure systems** including industrial control systems, and companies that have **bespoke IT**." NCSC separately notes that small/medium enterprises running standard commercial software should migrate largely transparently via vendor updates on the same general timeline, without needing their own discovery program.

**Confidence:** Official national guidance from the UK's technical authority for cyber security — a strong, dated, and unusually concrete recommendation (three explicit calendar milestones), but formally advisory rather than a legal mandate, except insofar as NCSC guidance is adopted into sector-specific regulation (e.g., for UK CNI operators under NIS Regulations) — no such binding transposition was found in this research.

---

## 7. Binding regulatory deadlines — finance and other sectors

**PCI DSS 4.0 Requirement 12.3.3 (payments industry):**
- **Document:** PCI DSS v4.0 (and 4.0.1), Requirement 12.3.3, PCI Security Standards Council.
- **Effective/enforcement date:** **31 March 2025** (this "future-dated" requirement, defined when PCI DSS 4.0 was published, became mandatory/enforced on this date).
- **What it actually requires:** Organizations must maintain an **up-to-date, documented inventory of all cryptographic cipher suites and protocols in use**, including where and why each is used; **actively monitor industry/technology trends** (explicitly including developments like NIST's PQC standardization) regarding continued viability of those ciphers/protocols; and maintain a **documented response plan** for anticipated cryptographic deprecation/obsolescence, reviewed at least every 12 months.
- **Important caveat:** PCI DSS 4.0 does **not** currently mandate actual deployment of PQC algorithms — 12.3.3 mandates inventory + monitoring + planning only. It is a binding compliance requirement (non-compliance affects PCI DSS certification/attestation) but is a "readiness" requirement, not a "migrate by date X" requirement.
- **Scope:** Any entity that stores, processes, or transmits cardholder data (merchants, payment processors, service providers) — global payments industry, not government-specific.
- **Confidence:** Binding contractual/industry-compliance mandate (required for PCI DSS certification), already in force as of 31 March 2025.

**NIST IR 8547 (US, cross-cutting, referenced from NIST's PQC project page):**
- NIST's own PQC migration project page (csrc.nist.gov/projects/post-quantum-cryptography) states: **"NIST will deprecate and ultimately remove quantum-vulnerable algorithms from its standards by 2035, with high-risk systems transitioning much earlier"** (per the transition timeline in NIST IR 8547). This is a cross-industry (not sector-specific) US federal standards deprecation timeline, distinct from CNSA 2.0's NSS-specific dates. It does not itself cross-reference other countries' timelines — no UK/France/Germany citations were found on that NIST page during this research.

---

## Summary comparison table

| Regime | Earliest concrete dated milestone found | Scope | Confidence |
|---|---|---|---|
| US NSA CNSA 2.0 | 2025 (support/prefer CNSA 2.0 for signing, browsers/servers); 2027 (NSS acquisition gate); 2030 (exclusive use, signing & networking) | National Security Systems + defense industrial base | Binding for NSS/contractors |
| Germany BSI TR-02102-1 (2026-01) | 31 Dec 2030 (very-high-protection systems fully transitioned) / 31 Dec 2031 (classical-only key agreement sunset) | German federal gov't systems; de facto industry standard | Official recommendation (binding for federal systems/BSI certification) |
| EU ETSI | No specific calendar date found — process-stage guidance only | Voluntary, telecom/IT industry-wide | Informal/voluntary |
| France ANSSI | ~2025 (mandatory hybrid PQC) / ~2030 ("not reasonable to purchase non-PQC products") | Industry broadly, gated via ANSSI certification ("visas") | Official position paper; binding via product certification channel |
| India NQM / DST Task Force (Feb 2026) | FY2027-28 (CBOM mandatory) / 2027 (CII foundations) | CII (tighter) + general enterprise/gov't (looser); tiered by sector | Official government roadmap; not yet codified law |
| UK NCSC | 2028 (discovery + initial plan complete) | Large organisations, CNI operators, bespoke-IT companies | Official recommendation, not legal mandate |
| PCI DSS 4.0 (12.3.3) | 31 March 2025 (already in force) | Global payments industry (merchants, processors) | Binding compliance requirement (inventory/monitoring only, not PQC deployment) |
| NIST IR 8547 (US, cross-sector) | 2035 (full deprecation of quantum-vulnerable algorithms); high-risk systems earlier | US federal standards, broad influence | Official federal standards timeline |

---

## Could not find

- **No CERT-In-specific PQC advisory** was located (India). The DST/NQM Task Force report is the only concrete Indian government artifact found; CERT-In does not appear to have issued its own separate binding cryptographic-migration advisory as of the research date.
- **No ETSI document with an explicit calendar deadline** (e.g., "migrate by 2030") was found — all ETSI PQC migration guidance located is process/methodology-based (inventory → plan → execute) without fixed dates.
- **No binding cross-EU regulatory deadline** (e.g., an EU Commission regulation or directive with a hard PQC migration date) was found; the "European roadmap...2035" reference appears in the BSI document but no independent EU-level regulatory source with that exact date was independently verified in this session.
- **No sector-specific binding regulation beyond PCI DSS** was found with a PQC-specific compliance deadline (e.g., no confirmed binding energy-grid, healthcare, or telecom regulation with a dated PQC mandate, in the US, EU, UK, France, Germany, or India, distinct from the national roadmaps already covered above).
- Two primary-source PDFs (NSA's CNSA 2.0 Algorithms annex, and the Indian DST Task Force full report) could not be directly text-extracted by the fetch tooling in this session (403 block and PDF binary-decode failure respectively); the timeline data attributed to them above rests on corroborating secondary sources, not a direct read of the primary PDF text, and should be re-verified against the primary document before being hardcoded as an authoritative deadline in any scoring engine.

---

## Sources

- NSA, *CSI: CNSA 2.0 FAQ* (Dec 2024, v2.1) — https://media.defense.gov/2022/Sep/07/2003071836/-1/1/1/CSI_CNSA_2.0_FAQ_.PDF
- NSA, *CNSA 2.0 Algorithms* advisory (PP-22-1338) — https://media.defense.gov/2025/May/30/2003728741/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS.PDF (403 on direct fetch; corroborated via https://www.encryptionconsulting.com/quantum-proof-with-cnsa-2-0/ and https://quantumsequrity.com/blog/cnsa-2-0-timeline-detailed)
- NSA, *NSA Releases Future Quantum-Resistant (QR) Algorithm Requirements for National Security Systems* — https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/3148990/
- BSI, *TR-02102-1 "Cryptographic Mechanisms: Recommendations and Key Lengths," Version 2026-01* — https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TG02102/BSI-TR-02102-1.html
- BSI, *Migration zu Post-Quanten-Kryptografie – Handlungsempfehlungen des BSI* — https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Krypto/Post-Quanten-Kryptografie.pdf
- ETSI, *TR 103 619 V1.1.1 (2020-07)* — https://www.etsi.org/deliver/etsi_tr/103600_103699/103619/01.01.01_60/tr_103619v010101p.pdf ; press release https://www.etsi.org/newsroom/press-releases/1805-2020-08-etsi-releases-migration-strategies-and-recommendations-for-quantum-safe-schemes
- ETSI, *TR 103 949 V1.1.1 (2023-05)* — https://www.etsi.org/deliver/etsi_tr/103900_103999/103949/01.01.01_60/tr_103949v010101p.pdf
- ANSSI, *ANSSI views on the Post-Quantum Cryptography transition* (4 Jan 2022) — https://cyber.gouv.fr/en/publications/anssi-views-post-quantum-cryptography-transition (mirrored at https://messervices.cyber.gouv.fr/guides/en-anssi-views-post-quantum-cryptography-transition)
- ANSSI, *FaQ sur la Cryptographie post-quantique* — https://cyber.gouv.fr/enjeux-technologiques/cryptographie-post-quantique/faq-pqc/
- ANSSI / G7, *Post-Quantum Cryptography Transition: ANSSI and Its G7 Partners...* — https://cyber.gouv.fr/en/news/post-quantum-cryptography-transition-anssi-and-its-g7-partners-rally-public-and-private-sectors-with-urgent-call-to-action/
- DST (Government of India), *Implementation of Quantum Safe Ecosystem in India — Report of the Task Force* (5 Feb 2026) — https://dst.gov.in/sites/default/files/Report_TaskForce_PQMigration_4Feb26%20(v1).pdf
- PostQuantum.com, *India's Task Force Releases Quantum-Safe Roadmap with 2027–2029 Migration Timeline for CII* — https://postquantum.com/security-pqc/indias-quantum-safe-roadmap/
- ORF, *India's Post-Quantum Cryptography Migration Roadmap* — https://www.orfonline.org/english/expert-speak/india-s-post-quantum-cryptography-migration-roadmap
- NCSC (UK), *Timelines for migration to post-quantum cryptography* (20 Mar 2025) — https://www.ncsc.gov.uk/guidance/pqc-migration-timelines
- NCSC (UK), *NCSC Annual Review 2025, Chapter 3: Migrating to post-quantum cryptography* — https://www.ncsc.gov.uk/collection/ncsc-annual-review-2025/chapter-03-keeping-pace-with-evolving-technology/migrating-to-post-quantum-cryptography
- NIST, *Post-Quantum Cryptography project page* (references NIST IR 8547 2035 deprecation timeline) — https://csrc.nist.gov/projects/post-quantum-cryptography
- PCI Security Standards Council context on Requirement 12.3.3 — https://www.guidepointsecurity.com/blog/pci-dss-4-0-major-future-dated-requirements/ ; https://www.qusecure.com/pci-dss-4-0-cryptographic-inventory/
- Repo file (internal, for comparison): `config/nqm_compliance.json`
