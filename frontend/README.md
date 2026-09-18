# ECDAT-X Frontend & Visualization

This directory contains the user interface for **ECDAT-X** (Enterprise Cryptographic Discovery, Analysis & Transformation Platform), built using **React 18**, **TypeScript**, **Vite**, **Tailwind CSS**, **Recharts**, and **React Flow**.

The frontend is specifically tailored for enterprise security analysts, auditors, and administrators to discover, visualize, and migrate vulnerable cryptography across enterprise architectures.

---

## 🚀 Quickstart

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run local development server
npm run dev

# 3. Typecheck
npm run typecheck

# 4. Build for production
npm run build
```

The app will be available at `http://localhost:5173`.

---

## 🎨 Design System: "Human" Light Enterprise Theme

In accordance with executive direction, the platform employs a refined, accessible **human light theme**:
- **Background:** Crisp, natural slate tints (`#f8fafc` page background, pure `#ffffff` cards and surfaces).
- **Typography:** High-contrast, legible slate scale (`slate-900` headings, `slate-600` body text, `slate-400` metadata).
- **Color Discipline:** Eliminates harsh neon glows, aggressive gradients, and excessive visual noise in favor of subtle borders, purposeful soft status badges (`red-50`, `amber-50`, `emerald-50`, `blue-50`), and clean chart palettes.
- **Accents:** Professional enterprise blue (`#2563eb` / `#3b82f6`) for primary navigation and actions.

---

## 📋 Resolved Issues & Feature Implementations

### 1. Issue #23 — Dashboard Light Theme & Navigation Architecture
- **Categorized Sidebar:** Restructured flat navigation into 4 logical enterprise domains:
  - **Discovery:** Dashboard, Upload Center, Asset Explorer, Knowledge Graph
  - **Intelligence:** Risk Analysis, Quantum Risk, Asset Intelligence, Blast Radius
  - **Migration:** Migration Planner, PQC Recommendations
  - **Enterprise:** Security Operations, Administration, Audit & Reports, Research Validation
- **Modern Active State:** Indicator tab using a left-border accent (`border-l-2 border-blue-500 bg-blue-50`) providing immediate orientation.
- **Hero Metrics Row:** Executive-grade KPI cards highlighting Total Assets Discovered, Critical Findings, Quantum Exposure Percentage, and Average Risk Score.
- **Quick Actions Bar:** One-click shortcuts for Repository Scan, Blast Radius Simulation, and JSON Inventory Report Export.
- **Recent Scan Activity:** Clean audit trail showing real-time discovery jobs capped to the latest 5 runs with status badges.
- **Compound UI Extensions:** Added `CardHeader`, `CardTitle`, and `CardContent` components ensuring type safety and modular layout compositions.

### 2. Issue #16 — Blast Radius Animated Impact Propagation
- **Breadth-First Search (BFS) Topological Engine:** Dynamically calculates 1° (direct), 2° (secondary), and 3°+ (tertiary) dependency degrees originating from high-centrality crypto assets.
- **4-Frame Compromise Simulation:** Triggered via *"What if [asset] is compromised?"*:
  - **Frame 1:** Compromised asset highlights in designated alert state.
  - **Frame 2:** Directly connected applications transition to orange alert with active SVG edge animations.
  - **Frame 3:** Secondary services transition to warning amber.
  - **Frame 4:** Tertiary systems illuminate in lime/yellow alert.
- **Slide-in Impact Summary Panel:** Post-simulation drawer detailing exact impacted service counts broken down by dependency degree alongside actionable risk badges.

### 3. Issue #24 — Harvest Now, Decrypt Later (HNDL) Threat Timeline
- **Interactive 3-Zone Horizon:**
  - **Harvesting Window:** Real-time animated encrypted packet telemetry demonstrating present-day data collection by adversaries.
  - **Q-Day Horizon:** Dynamically positioned arrival boundary line.
  - **Decryption Era:** Burst visualization indicating where harvested ciphertexts become retroactively readable.
- **Interactive Horizon Slider (2028–2045):** Allows security leadership to adjust Q-Day estimates and immediately view systemic exposure impact.
- **Per-Asset Exposure Assessment Cards:** Evaluates asset data retention lifetime against time-to-quantum:
  - 🔴 **At Risk:** Retention lifetime outlasts time to Q-Day (data remains confidential when quantum decryption becomes feasible).
  - 🟢 **Safe:** Data retention naturally expires prior to quantum arrival.

### 4. Issue #25 — Migration Roadmap Gantt Chart
- **Visual Multi-Wave Sequencing:** Interactive timeline representing dependency-aware phased migration:
  - **Wave 1 — Foundations:** Cryptographic trust anchors, roots of trust, and core algorithms (Months 1–6).
  - **Wave 2 — Libraries:** Middleware, protocol layers, and shared cryptography SDKs (Months 4–12).
  - **Wave 3 — Applications:** End-user applications, business workflows, and external APIs (Months 10–18).
- **Interactive Wave Inspector:** Clicking any timeline bar or wave header expands a detailed work breakdown schedule showing current algorithms, NIST-standardized PQC replacements (ML-KEM, ML-DSA), complexity tiers, and estimated engineering hours.
- **Dependency Guardrails:** Visual sequencing indicators illustrating strict prerequisite requirements between waves.

### 5. Issue #33 — Knowledge Graph Topology Polish
- **Real-Time Node Search & Filter:** Instant search box highlighting target primitives (e.g., `RSA-2048`, `ECDSA`) across the entire dependency graph.
- **Degree-Weighted Node Sizing:** Node dimensions and typography scale proportionately to topological centrality and edge count, making architectural bottlenecks instantly discernible.
- **Interactive Legend Controls:** Node type pills (Projects, Applications, Services, Libraries, Protocols, Algorithms, Certificates) double as interactive filter toggles.
- **Comprehensive Asset Inspector:** Sliding inspection panel reporting cryptographic properties, locations, PQC recommendations, relationship counts, and severity ratings.

---

## 🛠️ Tech Stack & Key Libraries

| Capability | Library |
|---|---|
| UI Framework | React 18, TypeScript |
| Build Tool | Vite |
| Styling & Theming | Tailwind CSS (v4) |
| Topology & Flow Graphs | React Flow (`reactflow`) |
| Data Visualizations | Recharts |
| Iconography | Lucide React |
| HTTP & API Client | Axios |

---

## 📁 Source File Directory

```text
frontend/src/
├── api/             # Typed API client functions and error handlers
├── auth/            # JWT authentication context and session persistence
├── components/
│   ├── Layout.tsx   # Enterprise header, responsive grouped sidebar & breadcrumbs
│   └── ui.tsx       # Reusable UI primitives (Card, Badges, Headers, States)
├── hooks/           # useAsync data-fetching and lifecycle hooks
├── pages/
│   ├── Dashboard.tsx            # Executive KPI & risk distribution overview
│   ├── BlastRadius.tsx          # Animated cryptographic blast radius visualizer
│   ├── QuantumRiskDashboard.tsx # Quantum vulnerability & HNDL timeline
│   ├── MigrationPlanner.tsx     # 3-wave roadmap with interactive Gantt chart
│   ├── KnowledgeGraph.tsx       # Topology explorer with search & degree sizing
│   ├── AssetExplorer.tsx        # Cryptographic asset inventory table
│   ├── AssetIntelligence.tsx    # Evidence correlation and business context
│   ├── UploadCenter.tsx         # Repository, container & TLS discovery scans
│   ├── RiskAnalysis.tsx         # Detailed rule and factor breakdown
│   ├── PQCRecommendations.tsx   # ML-KEM / ML-DSA candidate mappings
│   ├── SecurityOperations.tsx   # Central operational health dashboard
│   ├── AdminDashboard.tsx       # Multi-tenant and user role administration
│   ├── AuditorView.tsx          # Immutable audit trails & PDF/JSON exports
│   ├── ValidationDashboard.tsx  # Benchmark execution metrics
│   └── Login.tsx                # Enterprise authentication gateway
├── types/api.ts     # TypeScript interface definitions mirroring backend models
└── utils/format.ts  # Formatting helpers and severity badge styles
```

---

## 🧪 Verification & Quality Control

To verify the frontend implementation:
```bash
# Typecheck
npm run typecheck

# Production build check
npm run build
```
Both commands validate clean compilation with zero warnings or errors.
