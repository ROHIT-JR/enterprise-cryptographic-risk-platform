export type Severity = "critical" | "high" | "medium" | "low";
export type Criticality = Severity;
export type ScanStatus = "queued" | "running" | "completed" | "failed";
export type ScanSource = "repository" | "docker" | "tls";

export interface DistributionItem {
  name: string;
  value: number;
}

export interface Scan {
  id: string;
  organization_id: string;
  project_id: string;
  source_type: ScanSource;
  target: string;
  status: ScanStatus;
  progress: number;
  error_message: string | null;
  summary: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DashboardData {
  metrics: {
    total_assets: number;
    critical_assets: number;
    high_assets: number;
    algorithms_found: number;
    projects_scanned: number;
    quantum_exposure_percent?: number;
    average_risk_score?: number;
  };
  risk_distribution: DistributionItem[];
  algorithm_distribution: DistributionItem[];
  recent_scans: Scan[];
}

export interface AssetRisk {
  score: number;
  severity: Severity;
  reasons: string[];
}

export interface Asset {
  id: string;
  organization_id: string;
  project_id: string;
  project_name: string;
  scan_id: string;
  type: string;
  name: string;
  algorithm: string | null;
  version: string | null;
  location: string;
  evidence: string;
  confidence: number;
  dependency_count: number;
  details: Record<string, unknown>;
  risk: AssetRisk | null;
  created_at: string;
}

export interface AssetPage {
  items: Asset[];
  total: number;
  page: number;
  page_size: number;
}

export interface RiskFactor {
  category: string;
  points: number;
  explanation: string;
  rule_id: string;
}

export interface RiskFinding {
  id: string;
  organization_id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  algorithm: string | null;
  project_id: string;
  project_name: string;
  score: number;
  severity: Severity;
  reasons: string[];
  factors: RiskFactor[];
  location: string;
  evidence: string;
  created_at: string;
}

export interface RiskPage {
  items: RiskFinding[];
  total: number;
  page: number;
  page_size: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  source: "neo4j" | "postgresql";
}

export interface IntelligenceItem {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  algorithm: string | null;
  project_id: string;
  project_name: string;
  quantum_score: number;
  quantum_classification: string;
  hndl_score: number;
  hndl_risk: Severity;
  centrality_score: number;
  dependent_systems: number;
  business_score: number;
  migration_complexity_score: number;
  evidence_confidence: number;
  evidence_sources: string[];
  final_score: number;
  severity: Severity;
  explanations: string[];
  factors: Record<string, unknown>;
}

export interface IntelligenceRiskData {
  metrics: {
    total_analyzed: number;
    vulnerable_assets: number;
    critical_quantum_risks: number;
    hndl_exposures: number;
    average_risk_score: number;
  };
  algorithm_vulnerability_distribution: DistributionItem[];
  severity_distribution: DistributionItem[];
  items: IntelligenceItem[];
}

export interface BlastRadiusData {
  asset_id: string | null;
  asset_name: string | null;
  dependent_systems: number;
  centrality_score: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface MigrationRecommendation {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  current_algorithm: string;
  recommended_algorithm: string;
  wave: number;
  complexity: string;
  risk_score: number | null;
  reasons: string[];
  recommendation: {
    hybrid_strategy?: string;
    reason?: string;
    metrics?: Record<string, string>;
    constraints?: string[];
  };
}

export interface MigrationRoadmap {
  total_assets: number;
  waves: Array<{
    wave: number;
    title: string;
    reason: string;
    items: MigrationRecommendation[];
  }>;
}

export type MoscaVerdict = "critical" | "plan" | "safe";

export interface MoscaAssetResult {
  asset_id: string;
  asset_name: string;
  algorithm: string | null;
  data_lifetime_years: number;
  migration_time_years: number;
  lhs: number;
  verdict: MoscaVerdict;
}

export interface MoscaSimulateResponse {
  organization_status: MoscaVerdict;
  quantum_arrival_year: number;
  current_year: number;
  years_until_quantum: number;
  critical_count: number;
  plan_count: number;
  safe_count: number;
  total_assets: number;
  most_urgent_asset: string | null;
  formula: string;
  items: MoscaAssetResult[];
}

export interface NQMRequirement {
  id: string;
  label: string;
  complete: boolean;
  progress: number;
  evidence: string;
}

export interface NQMPhase {
  id: number;
  name: string;
  years: string;
  description: string;
  progress: number;
  status: "complete" | "in-progress" | "not-started";
  requirements: NQMRequirement[];
}

export interface SectorProfile {
  id: string;
  name: string;
  match_industries: string[];
  regulator: string;
  guidance: string;
  priority_assets: string[];
  recommended_baseline: string;
}

export interface NQMComplianceReport {
  source: string;
  organization_id: string;
  organization_name: string;
  current_phase: number;
  overall_progress: number;
  phases: NQMPhase[];
  sector: SectorProfile;
}

export type UserRole = "administrator" | "security_analyst" | "auditor" | "viewer";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  organization_id: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
}

export interface Organization {
  id: string;
  name: string;
  industry: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface EnterpriseOverview {
  organizations: number;
  users: number;
  projects: number;
  scans: number;
  assets: number;
  critical_risks: number;
  migration_assets: number;
  recent_audit: AuditLog[];
}

export interface FullHealth {
  backend: string;
  postgres: string;
  neo4j: string;
  scanner_engine: string;
  scanners: string[];
}

export type BenchmarkKind = "kem" | "signature";

export interface BenchmarkTimings {
  keygen_us: number;
  encaps_us?: number;
  decaps_us?: number;
  sign_us?: number;
  verify_us?: number;
}

export interface BenchmarkSizes {
  pk_bytes: number;
  sk_bytes: number;
  ct_bytes?: number;
  sig_bytes?: number;
}

export interface BenchmarkAlgorithm {
  name: string;
  family: string;
  kind: BenchmarkKind;
  standard: string;
  standard_year: number;
  quantum_safe: boolean;
  nist_category: number | null;
  classical_security_bits: number | null;
  timings_us: BenchmarkTimings;
  measured_us: Partial<BenchmarkTimings> | null;
  sizes_bytes: BenchmarkSizes;
  handshake_ops_us: number;
  wire_bytes: number;
  timing_source: string;
  size_source: string;
  scores: {
    speed: number;
    compactness: number;
    maturity: number;
    quantum_security: number;
  };
}

export interface BenchmarkRun {
  started_at: string;
  duration_s: number;
  iterations: number;
  environment: {
    python: string;
    platform: string;
    machine: string;
    cryptography: string | null;
    liboqs_python: string | null;
    oqs_available: boolean;
  };
  measured: Record<string, Partial<BenchmarkTimings>>;
  skipped: Record<string, string>;
}

export interface BenchmarkCatalogue {
  schema_version: number;
  description: string;
  sources: Record<string, string>;
  tls_model: {
    initial_congestion_window_bytes: number;
    cert_overhead_bytes: number;
    default_chain_certs: number;
  };
  algorithms: BenchmarkAlgorithm[];
  latest_run: BenchmarkRun | null;
}

export interface HandshakeProfile {
  key_exchange: string;
  key_exchange_mode: "kem" | "rsa-key-transport";
  authentication: string;
  client_cpu_us: number;
  server_cpu_us: number;
  total_cpu_us: number;
  certificate_chain_bytes: number;
  client_flight_bytes: number;
  server_flight_bytes: number;
  total_bytes: number;
  exceeds_initial_cwnd: boolean;
  key_exchange_quantum_safe: boolean;
  authentication_quantum_safe: boolean;
}

export interface MigrationImpact {
  chain_certs: number;
  assumptions: {
    cert_overhead_bytes: number;
    initial_congestion_window_bytes: number;
    note: string;
  };
  before: HandshakeProfile;
  after: HandshakeProfile;
  delta: {
    cpu_percent: number;
    cpu_us: number;
    bytes: number;
    bytes_percent: number;
    certificate_chain_bytes: number;
    certificate_chain_percent: number;
  };
}

export interface MigrationImpactQuery {
  kex_from: string;
  kex_to: string;
  auth_from: string;
  auth_to: string;
  chain_certs: number;
}

export type VerificationCheckStatus = "pass" | "warn" | "fail" | "pending";
export type VerificationOverall = "verified" | "conditional" | "pending" | "blocked";

export interface VerificationCheck {
  id: string;
  title: string;
  status: VerificationCheckStatus;
  basis: "computed" | "policy" | "generated";
  evidence: string[];
}

export interface HybridStep {
  step: number;
  title: string;
  description: string;
  duration_days: number;
  exit_criteria: string;
}

export interface VerificationTestResult {
  id: string;
  name: string;
  measured: string;
  threshold: string;
  status: "pass" | "fail" | "pending";
  basis: "benchmark" | "model" | "simulated";
  detail: string;
}

export interface MigrationVerification {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  wave: number;
  current_algorithm: string;
  recommended_algorithm: string;
  target_kind: "algorithm" | "integration";
  targets: string[];
  overall: VerificationOverall;
  checks: VerificationCheck[];
  hybrid_steps: HybridStep[];
  rollback_plan: string[];
  test_results: VerificationTestResult[];
}

export interface MigrationVerificationReport {
  thresholds: Record<string, number>;
  hybrid_schedule_days: Record<string, number>;
  summary: {
    total: number;
    verified: number;
    conditional: number;
    pending: number;
    blocked: number;
    checks: Record<string, Record<VerificationCheckStatus, number>>;
  };
  items: MigrationVerification[];
}

export interface ValidationStage {
  status: "measured" | "skipped";
  duration_ms?: number;
  reason?: string;
}

export interface ValidationExperiment {
  nodes: number;
  topology: string;
  graph_nodes: number;
  graph_edges: number;
  total_duration_ms: number;
  stages: Record<string, ValidationStage | undefined>;
}

export interface ValidationBaseline {
  benchmark_version: string;
  timestamp: string;
  environment?: { python?: string; platform?: string; cpu?: string };
  experiments: ValidationExperiment[];
}

export interface ValidationEnvelope {
  status: "success" | "empty" | "error";
  message: string;
  data: Partial<ValidationBaseline>;
}
