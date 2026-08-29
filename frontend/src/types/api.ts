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
