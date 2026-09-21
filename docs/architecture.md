# ECDAT-X architecture

This page explains how ECDAT-X is built and why. Each diagram is drawn from the code as it is
today. Two of them (the database schema and the TOPSIS worked example) are **generated** from the
models and the solver, and a test fails if they go stale.

- [1. System architecture](#1-system-architecture)
- [2. Deployment topology](#2-deployment-topology)
- [3. Data flow: upload to report](#3-data-flow-upload-to-report)
- [4. Risk scoring methodology](#4-risk-scoring-methodology)
- [5. Migration decisions: TOPSIS](#5-migration-decisions-topsis)
- [6. Database schema](#6-database-schema)
- [7. Component boundaries](#7-component-boundaries)
- [8. Scanner plugin contract](#8-scanner-plugin-contract)
- [9. CBOM design](#9-cbom-design)
- [10. Failure behavior and scaling](#10-failure-behavior-and-scaling)

## Design goals

ECDAT-X sits between raw scanner evidence and PQC migration decisions. It prioritizes evidence
retention, deterministic and explainable analysis, scanner extensibility, tenant isolation, and
graceful degradation when an optional service (Neo4j) is down.

## 1. System architecture

Requests enter through the FastAPI middleware, are authenticated and tenant-scoped, and reach
thin routers. Routers delegate to services, which call the domain engines. The engines contain the
actual cryptographic and decision logic and know nothing about HTTP or the database.

```mermaid
flowchart TB
    subgraph CLIENTS["Clients"]
        BROWSER["React + TypeScript dashboard<br/>Vite, React Flow, Recharts"]
        TOOLS["curl, scripts, Swagger UI"]
    end
    GATEWAY["Nginx gateway<br/>production only: request limit, one origin"]

    subgraph API["FastAPI backend"]
        direction TB
        MW["Middleware: request ID, security headers, CORS, rate limit"]
        AUTH["JWT auth + RBAC: 4 roles, organization scope"]
        ROUTERS["Routers grouped by feature area<br/>Discovery, Intelligence, Migration, Enterprise, Research and Validation"]
        subgraph SERVICES["Services"]
            direction LR
            ORCH["Scan orchestrator<br/>background job, progress events"]
            INTEL["Intelligence service<br/>risk analysis, migration plans"]
            REPORT["Report and CBOM service"]
            OTHER["Lifecycle, compliance,<br/>verification, audit"]
        end
        MW --> AUTH --> ROUTERS --> SERVICES
    end

    subgraph ENGINES["Domain engines: pure logic, no HTTP or database"]
        direction LR
        SCANNERS["Scanner plugins<br/>repository, docker, tls"]
        RISK["risk_engine<br/>quantum, HNDL, centrality,<br/>Mosca, crypto-agility"]
        MIG["migration_engine<br/>TOPSIS, roadmap,<br/>optimizer, verification"]
        CBOM["cbom_engine<br/>CycloneDX 1.6"]
        LIFE["lifecycle_engine<br/>state machine"]
        GRAPHA["graph_analysis<br/>NetworkX"]
        BENCH["benchmarks<br/>PQC vs classical"]
    end

    subgraph DATA["Data stores"]
        direction LR
        PG[("PostgreSQL<br/>authoritative")]
        NEO[("Neo4j<br/>rebuildable projection")]
        FS[("scan-data volume<br/>uploaded archives")]
    end

    subgraph TARGETS["Scan targets"]
        direction LR
        REPO["Repository ZIPs"]
        IMG["Container images<br/>via Docker"]
        TLS["Live TLS endpoints"]
    end

    BROWSER --> GATEWAY --> MW
    TOOLS --> MW
    ORCH --> SCANNERS
    ORCH --> INTEL
    INTEL --> RISK
    INTEL --> MIG
    INTEL --> GRAPHA
    REPORT --> CBOM
    OTHER --> LIFE
    OTHER --> BENCH
    SCANNERS --> TARGETS
    SERVICES --> PG
    ORCH -.->|"best effort"| NEO
    ORCH --> FS
```

PostgreSQL is authoritative for projects, scans, assets, relationships, risk and migration data.
Neo4j is a rebuildable projection; if it is unavailable the graph API keeps working from
PostgreSQL. In local development the browser talks to the API directly (allowed by an exact-origin
CORS list); in production the Nginx gateway puts both behind one origin.

## 2. Deployment topology

The development stack is a Docker Compose file with PostgreSQL, Neo4j, the API and the Vite
frontend, with source mounted for live reload:

```mermaid
flowchart TD
    USER["Developer browser"] -->|"localhost:5173"| UI["React + Vite"]
    UI -->|"localhost:8000"| API["FastAPI"]
    API -->|"postgres:5432"| PG[("PostgreSQL 16")]
    API -->|"neo4j:7687"| NEO[("Neo4j 5.26")]
```

The production profile (`deployment/docker-compose.prod.yml`) adds an Nginx gateway, publishes a
single port, and puts the databases on an internal-only network so only the API can reach them:

```mermaid
flowchart LR
    USER["User"] -->|"HTTP(S) :8080"| GW["Nginx gateway<br/>10 req/s per client"]
    GW -->|"/api /health /docs /redoc"| API["FastAPI"]
    GW -->|"everything else"| UI["Static frontend"]
    subgraph DATA["Internal network only"]
        PG[("PostgreSQL")]
        NEO[("Neo4j")]
    end
    API --> PG
    API --> NEO
```

## 3. Data flow: upload to report

Everything a user sees is produced by one background job per scan. The job reports progress at
each stage, which the API exposes both by polling (`GET /scans/{scan_id}`) and as a live
Server-Sent Events feed (`GET /scans/{scan_id}/stream`).

```mermaid
flowchart LR
    subgraph INTAKE["Intake"]
        direction TB
        UPLOAD["1. Upload<br/>POST /scans/repository, /docker or /tls<br/>returns 202 with a queued scan"]
        SCAN["2. Scan (20%)<br/>the matching scanner plugin runs<br/>and returns findings with evidence"]
        INVENTORY["3. Inventory (45 to 65%)<br/>normalize and fingerprint findings,<br/>persist assets and relationships"]
        UPLOAD --> SCAN --> INVENTORY
    end
    subgraph ANALYSIS["Analysis"]
        direction TB
        BASELINE["4. Baseline risk (65%)<br/>rule engine scores every asset"]
        INTEL["5. Intelligence (70 to 74%)<br/>six factors become the final score<br/>and replace the baseline"]
        MIGRATION["6. Migration plans<br/>TOPSIS picks the PQC algorithm,<br/>the optimizer orders the waves"]
        BASELINE --> INTEL --> MIGRATION
    end
    subgraph OUTPUT["Outputs"]
        direction TB
        CBOM["7. CBOM (78%)<br/>CycloneDX 1.6 document"]
        GRAPH["8. Graph sync (88%)<br/>project into Neo4j, best effort"]
        DONE["9. Done (100%)<br/>summary saved, audit event written"]
        REPORT["10. Report<br/>GET /reports/type?format=json, pdf or cbom<br/>every export is audited"]
        CBOM --> GRAPH --> DONE --> REPORT
        DONE -.-> STREAM["Live progress feed<br/>GET /scans/id/stream"]
    end
    INTAKE --> ANALYSIS --> OUTPUT
```

The same flow as a sequence, including who talks to whom:

```mermaid
sequenceDiagram
    actor Analyst
    participant UI as React dashboard
    participant API as FastAPI
    participant Job as Scan orchestrator
    participant Plugin as Scanner plugin
    participant Intel as Intelligence service
    participant CBOM as CBOM engine
    participant PG as PostgreSQL
    participant Neo as Neo4j

    Analyst->>UI: Submit a repository, image or endpoint
    UI->>API: POST /scans/{source}
    API->>PG: Create a queued scan
    API-->>UI: 202 with the scan ID
    API->>Job: Start the background job
    UI->>API: GET /scans/{id}/stream
    Job->>Plugin: Analyze the validated target
    Plugin-->>Job: Assets, evidence, relationships
    Job->>PG: Persist the normalized inventory
    Job->>Intel: Analyze the project
    Intel->>PG: Save risk analysis and migration plans
    Job->>CBOM: Generate the CBOM
    Job->>Neo: Project nodes and edges (best effort)
    Job->>PG: Mark the scan completed
    API-->>UI: completed event, stream closes
    Analyst->>UI: Open dashboards, export a report
```

## 4. Risk scoring methodology

Scoring happens in two stages. A **rule-based baseline** scores each asset as soon as it is
persisted (severity: critical at 75 and above, high at 50, medium at 25). The **intelligence
stage** then computes the six-factor score below and *replaces* the baseline finding with it, so
the numbers analysts see everywhere are the six-factor ones.

```mermaid
flowchart LR
    subgraph INPUTS["What we know about an asset"]
        ALGO["Algorithm"]
        DATA["Data sensitivity and lifetime"]
        GRAPH["Dependency graph"]
        BIZ["Business criticality"]
        MIGX["Dependents, legacy tech,<br/>downtime, compatibility"]
        EVID["Evidence from several channels"]
    end

    ALGO --> Q["Quantum vulnerability<br/>lookup, 0 to 100"]
    ALGO --> H["HNDL exposure<br/>0 to 100"]
    DATA --> H
    GRAPH --> C["Dependency centrality<br/>0 to 100"]
    BIZ --> B["Business criticality<br/>20, 50, 75 or 100"]
    MIGX --> M["Migration complexity<br/>additive points, capped at 100"]
    EVID --> E["Evidence confidence<br/>Dempster-Shafer fusion"]

    Q -->|"x 0.30"| SUM["Weighted sum<br/>rounded, capped at 100"]
    H -->|"x 0.20"| SUM
    C -->|"x 0.15"| SUM
    B -->|"x 0.15"| SUM
    M -->|"x 0.10"| SUM
    E -->|"x 0.10"| SUM

    SUM --> SEV{"Severity"}
    SEV -->|"0 to 30"| LOW["Low"]
    SEV -->|"31 to 60"| MED["Medium"]
    SEV -->|"61 to 80"| HIGH["High"]
    SEV -->|"81 to 100"| CRIT["Critical"]
```

| Factor | Weight | How it is computed |
|---|---:|---|
| Quantum vulnerability | 30% | Lookup in `risk_engine/algorithm_risks.json`. RSA, ECC, ECDH and Diffie-Hellman score 100 (Shor's algorithm breaks them). MD5 70, AES-128 50, AES-256 20, SHA-256 15, ML-KEM 0, and unknown algorithms 25. |
| HNDL exposure | 20% | `0.4 x sensitivity + 0.3 x min((data lifetime + exposure years) x 5, 100) + 0.3 x (100 if quantum-vulnerable)`. Sensitivity: public 0, internal 30, confidential 70, regulated, financial and restricted 100. |
| Dependency centrality | 15% | `0.3 x degree + 0.5 x dependents / max dependents + 0.2 x share of critical dependents`, scaled to 100. Uses the same relationships as the graph. |
| Business criticality | 15% | low 20, medium 50, high 75, critical 100. |
| Migration complexity | 10% | Points: 10 to 30 for dependent applications, 15 for legacy technology, 10 to 15 for a critical service, 20 for zero downtime, 20 for limited PQC compatibility. Capped at 100. |
| Evidence confidence | 10% | Dempster-Shafer combination of independent evidence channels (source, Docker, TLS, certificate, library). When channels conflict above 0.7 it falls back to a simple average. |

Every result carries the per-factor contributions and plain-language reasons, so a score can
always be explained. The **Mosca inequality** (`X + Y > Z`: years the data must stay secret plus
years to migrate, against years until a quantum computer arrives) is a separate lens on the same
assets. It answers "must we start now?" rather than "how risky is this?" and is explorable at
`/quantum-risk`.

## 5. Migration decisions: TOPSIS

For each quantum-vulnerable asset the recommender decides *which* PQC algorithm to use in four steps:

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 420, "rankSpacing": 28}}}%%
flowchart TD
    A["Asset using a quantum-vulnerable algorithm"] --> B["Classify its function: key establishment or signature<br/>(symmetric and hash algorithms need no replacement)"]
    B --> C["Hard filter: keep candidates at or above the required NIST security level"]
    C --> D["Build the decision matrix: one row per candidate, six criteria"]
    D --> E["TOPSIS: normalize, weight, then measure the distance<br/>to the ideal and the anti-ideal solution"]
    E --> F["Rank by closeness coefficient C: the top candidate is recommended"]
    F --> G["Add a hybrid transition strategy: classical + PQC during migration"]
```

TOPSIS ranks each candidate by how close it is to the best possible outcome on every criterion
at once and how far it is from the worst. Four criteria are *benefits* (higher is better) and
two are *costs* (lower is better: public key size and ciphertext size), with the weights shown
below.

One consequence is worth knowing: **security level is a hard floor, not a weighted criterion.**
With the default floor (NIST level 1) the smallest and fastest parameter set wins, which is why
`ML-KEM-512` is chosen by default. Raising `required_security_level` changes the answer, as the
last table shows. The tables below are generated by running the real solver over the real
knowledge base for a key-establishment asset (for example RSA or ECDH):

<!-- topsis-example:start -->
**Step 1: the decision matrix** (raw values from the knowledge base)

| Candidate | performance rank | public key (B) | ciphertext (B) | maturity | compatibility | ease of migration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ML-KEM-512 | 3 | 800 | 768 | 1.0 | 0.85 | 0.8 |
| ML-KEM-768 | 2 | 1184 | 1088 | 1.0 | 0.9 | 0.7 |
| ML-KEM-1024 | 1 | 1568 | 1568 | 1.0 | 0.8 | 0.6 |

Weights: performance rank 0.20 (benefit), public key (B) 0.15 (cost), ciphertext (B) 0.15 (cost), maturity 0.15 (benefit), compatibility 0.20 (benefit), ease of migration 0.15 (benefit)

**Step 2: normalize and weight, then find the ideal and anti-ideal solutions**

| Candidate | performance rank | public key (B) | ciphertext (B) | maturity | compatibility | ease of migration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ML-KEM-512 | 0.1604 | 0.0566 | 0.0560 | 0.0866 | 0.1153 | 0.0983 |
| ML-KEM-768 | 0.1069 | 0.0837 | 0.0793 | 0.0866 | 0.1221 | 0.0860 |
| ML-KEM-1024 | 0.0535 | 0.1109 | 0.1143 | 0.0866 | 0.1086 | 0.0737 |
| **Ideal (best)** | 0.1604 | 0.0566 | 0.0560 | 0.0866 | 0.1221 | 0.0983 |
| **Anti-ideal (worst)** | 0.0535 | 0.1109 | 0.1143 | 0.0866 | 0.1086 | 0.0737 |

**Step 3: distance to each, and the closeness coefficient** `C = D− / (D+ + D−)`

| Rank | Candidate | D+ (to ideal) | D− (to anti-ideal) | Closeness C |
| --- | --- | ---: | ---: | ---: |
| 1 | ML-KEM-512 | 0.0068 | 0.1358 | 0.9524 |
| 2 | ML-KEM-768 | 0.0655 | 0.0718 | 0.5229 |
| 3 | ML-KEM-1024 | 0.1363 | 0.0000 | 0.0000 |

**The same decision with a stricter security floor** (`required_security_level = 3`)

| Rank | Candidate | Closeness C |
| --- | --- | ---: |
| 1 | ML-KEM-768 | 1.0000 |
| 2 | ML-KEM-1024 | 0.0000 |
<!-- topsis-example:end -->

Signature candidates (ML-DSA and SLH-DSA) are ranked the same way against their own criteria.
Recommendations can be verified afterwards against benchmark data and policy limits; see
`GET /analytics/validation/migrations` in the [API guide](api-guide.md).

## 6. Database schema

The inventory and analysis tables, generated from the SQLAlchemy models. Every domain table also
carries `organization_id` (and most `project_id`) copied onto it for tenant isolation and fast
filtering. Those repeated edges are omitted from the diagram; the columns are still listed on
each table, marked `FK`. A `||--o|` edge means at most one child row (for example one risk
analysis per asset).

<!-- er-diagram:start -->
```mermaid
erDiagram
    ASSETS ||--o{ ASSET_RELATIONSHIPS : "source_asset_id"
    ASSETS ||--o{ ASSET_RELATIONSHIPS : "target_asset_id"
    PROJECTS ||--o{ ASSETS : "project_id"
    SCANS ||--o{ ASSETS : "scan_id"
    ORGANIZATIONS ||--o{ AUDIT_LOGS : "organization_id"
    USERS |o--o{ AUDIT_LOGS : "user_id"
    ASSETS ||--o| BUSINESS_CONTEXT : "asset_id"
    ASSETS ||--o{ CRYPTO_LIFECYCLE_EVENTS : "asset_id"
    USERS |o--o{ CRYPTO_LIFECYCLE_EVENTS : "actor_user_id"
    ASSETS ||--o| MIGRATION_PLAN : "asset_id"
    ORGANIZATIONS ||--o{ PROJECTS : "organization_id"
    USERS ||--o{ REFRESH_TOKENS : "user_id"
    ASSETS ||--o| RISK_ANALYSIS : "asset_id"
    ASSETS ||--o| RISK_FINDINGS : "asset_id"
    PROJECTS ||--o{ SCANS : "project_id"
    ORGANIZATIONS ||--o{ USERS : "organization_id"
    ASSET_RELATIONSHIPS {
        string id PK
        string organization_id FK
        string project_id FK
        string source_asset_id FK
        string target_asset_id FK
        string relationship_type
    }
    ASSETS {
        string id PK
        string organization_id FK
        string project_id FK
        string scan_id FK
        string asset_type
        string name
        string algorithm
        string lifecycle_state
        string governance_status
    }
    AUDIT_LOGS {
        string id PK
        string organization_id FK
        string user_id FK
        string action
        datetime timestamp
    }
    BUSINESS_CONTEXT {
        string id PK
        string asset_id FK
        string criticality
        int data_lifetime_years
        string data_sensitivity
    }
    CRYPTO_LIFECYCLE_EVENTS {
        string id PK
        string organization_id FK
        string project_id FK
        string asset_id FK
        string actor_user_id FK
        string previous_state
        string new_state
        string source
        int migration_wave
    }
    MIGRATION_PLAN {
        string id PK
        string organization_id FK
        string project_id FK
        string asset_id FK
        string recommended_algorithm
        int wave
        string complexity
        float priority_score
    }
    ORGANIZATIONS {
        string id PK
        string name
        string industry
    }
    PROJECTS {
        string id PK
        string organization_id FK
        string name
        string criticality
    }
    REFRESH_TOKENS {
        string id PK
        string user_id FK
        datetime expires_at
        datetime revoked_at
    }
    RISK_ANALYSIS {
        string id PK
        string organization_id FK
        string project_id FK
        string asset_id FK
        float quantum_score
        float hndl_score
        float centrality_score
        float final_score
        string severity
    }
    RISK_FINDINGS {
        string id PK
        string organization_id FK
        string project_id FK
        string asset_id FK
        float score
        string severity
    }
    SCANS {
        string id PK
        string organization_id FK
        string project_id FK
        string source_type
        string target
        string status
        int progress
    }
    USERS {
        string id PK
        string organization_id FK
        string username
        string email
        string role
        bool is_active
    }
```
<!-- er-diagram:end -->

- `organizations` own everything; `users` belong to one organization and hold a role.
- `refresh_tokens` store only a digest of each token, with revocation, so tokens can rotate.
- `projects` give business context. A `scans` row tracks target, state, progress, summary and the
  generated CBOM. `assets` retain identity, location, evidence, confidence and lifecycle state.
- `asset_relationships` store the `USES`, `CONTAINS`, `DEPENDS_ON` and `PROTECTS` edges, so the
  graph survives without Neo4j.
- `risk_findings` is what analysts see (score, severity, reasons, factors). `risk_analysis`
  keeps the six factor scores behind it.
- `migration_plan` holds the recommended algorithm, wave and reasoning per asset;
  `crypto_lifecycle_events` is the append-only history of every state change.
- `audit_logs` records who did what, per organization.

## 7. Component boundaries

| Component | Responsibility | Does not own |
|---|---|---|
| React dashboard | Analyst workflows and visualization | Scanning or risk policy |
| FastAPI routers | Validation, authorization, query contracts | Domain logic |
| Services | Orchestration and persistence | Detection rules, scoring formulas |
| Scan orchestrator | Scan lifecycle, normalization, engine coordination | Detection rules |
| Scanner registry | Plugin lookup by source type | Persistence |
| Risk engine | Transparent, explainable scoring | Graph storage or presentation |
| Migration engine | Algorithm selection, ordering, verification | Persistence |
| CBOM engine | Portable cryptographic inventory document | Database writes |
| Lifecycle engine | Asset state machine and its rules | Persistence |
| PostgreSQL | Authoritative operational data | Topology traversal optimization |
| Neo4j | Rebuildable relationship projection | Source-of-truth inventory |

## 8. Scanner plugin contract

Every plugin implements `ScannerPlugin`, declares a `ScanSource`, and returns a `ScanResult` of
normalized `DiscoveredAsset` and `DiscoveredRelationship` values. The orchestrator never branches
on scanner internals, so a new scanner is additive. The step-by-step guide, with a complete
worked example, is in [Scanner development](scanner-development.md).

## 9. CBOM design

The CBOM is a **CycloneDX 1.6** document (`bomFormat: CycloneDX`) that validates against the
official schema, so any CycloneDX tool can read it. Each cryptographic asset becomes a component
with a `bom-ref`, spec-defined algorithm primitives and crypto properties, dependency records, and
ECDAT-namespaced properties for evidence and risk score. A one-page and a multi-page PDF
rendition are produced from the same inventory.

## 10. Failure behavior and scaling

- Invalid or unsafe input marks a scan failed with an analyst-safe error message.
- A database failure prevents a `completed` status; a scan is never half-recorded as done.
- Neo4j failure adds a warning but never discards the inventory; graph reads fall back to PostgreSQL.
- Docker being unavailable fails only Docker scans.
- Certificate validation failures are recorded as evidence, not treated as a reason to stop
  collecting; the TLS scanner reconnects without verification and notes the error.
- **Scaling path:** background execution suits one API worker today. For multiple instances, move
  scan jobs behind a durable queue, put uploads in object storage, run scanners in restricted
  workers, and replace the per-process rate limiter and progress feed with a shared one. The scan
  state machine and engine boundaries already allow that without changing the API.
