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
