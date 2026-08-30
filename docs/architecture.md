# ECDAT-X architecture

## Phase 3 enterprise boundary

Phase 3 wraps the Phase 1–2 discovery and intelligence pipeline in identity, tenant, audit,
report, and deployment boundaries. PostgreSQL remains authoritative and Neo4j rebuildable.

```mermaid
flowchart LR
  USER[Admin / Analyst / Auditor / Viewer] --> JWT[JWT + RBAC]
  JWT --> API[Versioned FastAPI]
  API --> TENANT[Organization scope]
  TENANT --> PG[(PostgreSQL)]
  TENANT --> ORCH[Existing scan orchestrator]
  ORCH --> PLUGINS[Scanner plugin registry]
  PLUGINS --> DISCOVERY[Source / Docker / TLS]
  ORCH --> INTEL[Quantum risk + HNDL + migration]
  ORCH --> NEO[(Neo4j projection)]
  API --> REPORTS[JSON / PDF / CBOM reports]
  API --> AUDIT[Audit trail]
```

Access-token validation is stateless; refresh-token digests and revocation are relational. Tenant
IDs are denormalized onto high-volume domain tables for explicit, indexable isolation. A shared
limiter and asynchronous job queue are the first scale upgrades for multi-instance deployments.

## Design goals

Phase 1 establishes a reliable intelligence layer between raw scanner evidence and future PQC migration decisions. The architecture prioritizes evidence retention, deterministic analysis, scanner extensibility, and graceful degradation.

## Local deployment topology

The primary Phase 1 runtime is a four-service Docker Compose development stack:

```mermaid
flowchart TD
    USER[Developer browser] -->|localhost:5173| UI[React + Vite]
    UI -->|localhost:8000| API[FastAPI]
    API -->|postgres:5432| PG[(PostgreSQL)]
    API -->|neo4j:7687| NEO[(Neo4j)]
```

Compose uses development targets with source mounts and reload support. The same Dockerfiles retain production targets so a future hosted deployment can override environment variables without changing application boundaries.

## Component boundaries

| Component | Responsibility | Does not own |
|---|---|---|
| React dashboard | Analyst workflows and visualization | Scanning or risk policy |
| FastAPI API | Validation, job intake, query contracts | Scanner-specific detection |
| Scan orchestrator | Lifecycle, normalization, persistence, engine coordination | Detection rules |
| Scanner registry | Plugin discovery by source type | Persistence |
| CBOM engine | Portable cryptographic inventory document | Database writes |
| Risk engine | Transparent Phase 1 scoring | Graph storage or UI presentation |
| PostgreSQL | Authoritative operational data | Topology traversal optimization |
| Neo4j | Rebuildable relationship projection | Source-of-truth inventory |

## Scan sequence

```mermaid
sequenceDiagram
    actor Analyst
    participant UI as React dashboard
    participant API as FastAPI
    participant Job as Scan orchestrator
    participant Plugin as Scanner plugin
    participant Risk as Risk engine
    participant CBOM as CBOM engine
    participant PG as PostgreSQL
    participant Neo as Neo4j

    Analyst->>UI: Submit repository, image, or endpoint
    UI->>API: POST /scans/{source}
    API->>PG: Create queued scan
    API-->>UI: 202 + scan ID
    API->>Job: Background scan job
    Job->>Plugin: Analyze validated target
    Plugin-->>Job: Assets + evidence + relationships
    Job->>PG: Persist normalized inventory
    Job->>Risk: Score each asset
    Risk-->>Job: Score, severity, reasons, factors
    Job->>CBOM: Generate ECDAT-CBOM
    Job->>Neo: Project nodes and edges
    Job->>PG: Mark completed
    loop Until terminal state
        UI->>API: GET /scans/{id}
        API-->>UI: Progress and summary
    end
```

## Scanner plugin contract

Every plugin implements `ScannerPlugin`, declares a `ScanSource`, and returns a `ScanResult` containing normalized `DiscoveredAsset` and `DiscoveredRelationship` values. The orchestrator never branches on scanner implementation details beyond target preparation for repository archives.

This makes a future scanner additive:

1. Implement `ScannerPlugin.scan`.
2. Validate its target without a shell.
3. Return evidence-bearing domain objects.
4. Register it in `build_default_registry`.
5. Add an intake schema and API endpoint.

## Data model

```mermaid
erDiagram
    PROJECT ||--o{ SCAN : has
    PROJECT ||--o{ ASSET : owns
    SCAN ||--o{ ASSET : discovers
    ASSET ||--o| RISK_FINDING : receives
    ASSET ||--o{ ASSET_RELATIONSHIP : source
    ASSET ||--o{ ASSET_RELATIONSHIP : target
```

- `Project` provides business criticality context.
- `Scan` tracks target, source, state, progress, summary, and generated CBOM.
- `Asset` retains normalized identity, location, evidence, confidence, and source details.
- `RiskFinding` retains score, severity, human reasons, and machine-readable factor contributions.
- `AssetRelationship` stores `USES`, `CONTAINS`, `DEPENDS_ON`, and `PROTECTS` edges for resilience when Neo4j is unavailable.

## Risk model

Phase 1 applies:

```text
risk score = algorithm security + dependency impact + asset criticality + asset-specific rules
```

Scores are clamped to 100. Each contribution includes a stable rule ID, points, and explanation. Severity thresholds are Critical ≥ 75, High ≥ 50, Medium ≥ 25, and Low below 25. The risk model is deterministic and intentionally not predictive.

Future centrality or HNDL inputs can become additional factor providers without changing API response contracts.

## CBOM design

ECDAT-CBOM uses CycloneDX-inspired concepts: a serial number, metadata component, component `bom-ref` identifiers, crypto properties, dependency records, and ECDAT namespaced properties for evidence and risk. Phase 1 uses `bomFormat: ECDAT-CBOM` and `specVersion: 1.0`; a formal CycloneDX export adapter can be added alongside it.

## Failure behavior

- Invalid or unsafe inputs mark a scan failed with an analyst-safe error.
- PostgreSQL transaction failures prevent a completed status.
- Neo4j failure adds a warning but does not discard the authoritative inventory; graph reads fall back to PostgreSQL.
- Docker unavailability fails only Docker jobs.
- Certificate validation failures are evidence, not a collection blocker; the scanner reconnects without verification and records the error.

## Scaling path

The current background execution is appropriate for Phase 1 and a single API worker. Production scale should move scan jobs behind a durable queue, object storage, and dedicated restricted scanner workers. The `Scan` state machine and normalized engine boundaries are already compatible with that transition.
