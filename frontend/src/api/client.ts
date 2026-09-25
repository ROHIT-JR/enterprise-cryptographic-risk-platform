import axios from "axios";
import type {
  AssetPage,
  CryptoAgilityAssessment,
  Criticality,
  DashboardData,
  GraphData,
  BlastRadiusData,
  IntelligenceRiskData,
  MigrationRecommendation,
  MigrationRoadmap,
  MoscaSimulateResponse,
  NQMComplianceReport,
  RiskPage,
  Scan,
  AuthUser,
  UserRole,
  TokenResponse,
  Organization,
  AuditLog,
  EnterpriseOverview,
  FullHealth,
  BenchmarkCatalogue,
  MigrationImpact,
  MigrationImpactQuery,
  MigrationVerificationReport,
  ValidationEnvelope,
} from "../types/api";

const apiOrigin = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const apiBaseUrl = apiOrigin.endsWith("/api/v1") ? apiOrigin : `${apiOrigin}/api/v1`;

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60_000,
  headers: { Accept: "application/json" },
});

export type ReportType =
  | "executive-summary"
  | "technical"
  | "inventory"
  | "quantum-risk"
  | "migration"
  | "nqm-compliance";

/** `cbom` is the CycloneDX 1.6 JSON; `cbom-pdf` is its human-readable companion. */
export type ReportFormat = "json" | "pdf" | "cbom" | "cbom-pdf";

export function reportFilename(type: ReportType, format: ReportFormat): string {
  const date = new Date().toISOString().slice(0, 10).replaceAll("-", "");
  if (format === "cbom") return `ecdat-cbom-${date}.cdx.json`;
  if (format === "cbom-pdf") return `ecdat-cbom-${date}.pdf`;
  return `ecdat-${type}-${date}.${format}`;
}

export const authStorage = {
  access: () => sessionStorage.getItem("ecdat_access_token"),
  refresh: () => sessionStorage.getItem("ecdat_refresh_token"),
  user: (): AuthUser | null => {
    const value = sessionStorage.getItem("ecdat_user");
    return value ? (JSON.parse(value) as AuthUser) : null;
  },
  save: (tokens: TokenResponse) => {
    sessionStorage.setItem("ecdat_access_token", tokens.access_token);
    sessionStorage.setItem("ecdat_refresh_token", tokens.refresh_token);
    sessionStorage.setItem("ecdat_user", JSON.stringify(tokens.user));
  },
  clear: () => {
    sessionStorage.removeItem("ecdat_access_token");
    sessionStorage.removeItem("ecdat_refresh_token");
    sessionStorage.removeItem("ecdat_user");
  },
};

api.interceptors.request.use((config) => {
  const token = authStorage.access();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const dashboardApi = {
  get: async () => (await api.get<DashboardData>("/dashboard")).data,
};

export interface AssetFilters {
  search?: string;
  asset_type?: string;
  severity?: string;
  project_id?: string;
  page?: number;
  page_size?: number;
}

export const assetsApi = {
  list: async (filters: AssetFilters = {}) =>
    (await api.get<AssetPage>("/assets", { params: filters })).data,
};

export const risksApi = {
  list: async (params: { severity?: string; project_id?: string; page_size?: number } = {}) =>
    (await api.get<RiskPage>("/risks", { params })).data,
};

export const graphApi = {
  get: async (projectId?: string) =>
    (await api.get<GraphData>("/graph", { params: { project_id: projectId, limit: 700 } })).data,
};

export const scansApi = {
  get: async (id: string) => (await api.get<Scan>(`/scans/${id}`)).data,
  list: async () => (await api.get<Scan[]>("/scans")).data,
  repository: async (file: File, projectName: string, criticality: Criticality) => {
    const body = new FormData();
    body.append("file", file);
    body.append("project_name", projectName);
    body.append("criticality", criticality);
    return (await api.post<Scan>("/scans/repository", body)).data;
  },
  docker: async (image: string, projectName: string, criticality: Criticality) =>
    (
      await api.post<Scan>("/scans/docker", {
        image,
        project_name: projectName,
        criticality,
      })
    ).data,
  tls: async (endpoint: string, projectName: string, criticality: Criticality) =>
    (
      await api.post<Scan>("/scans/tls", {
        endpoint,
        project_name: projectName,
        criticality,
      })
    ).data,
  cbomUrl: (scanId: string) => `${api.defaults.baseURL}/scans/${scanId}/cbom`,
};

export const intelligenceApi = {
  risk: async () =>
    (await api.get<IntelligenceRiskData>("/intelligence/risk")).data,
  hndl: async () =>
    (await api.get<{ total: number; items: IntelligenceRiskData["items"] }>("/intelligence/hndl")).data,
  blastRadius: async (assetId?: string) =>
    (
      await api.get<BlastRadiusData>("/intelligence/blast-radius", {
        params: { asset_id: assetId, depth: 3 },
      })
    ).data,
  agility: async () =>
    (await api.get<CryptoAgilityAssessment>("/intelligence/agility")).data,
};

export const migrationApi = {
  recommendations: async () =>
    (await api.get<MigrationRecommendation[]>("/migration/recommendations")).data,
  roadmap: async () =>
    (await api.get<MigrationRoadmap>("/migration/roadmap")).data,
};

export const moscaApi = {
  simulate: async (quantumArrivalYear: number) =>
    (
      await api.post<MoscaSimulateResponse>("/mosca/simulate", {
        quantum_arrival_year: quantumArrivalYear,
      })
    ).data,
};

export const complianceApi = {
  nqm: async () => (await api.get<NQMComplianceReport>("/compliance/nqm")).data,
};

export const authApi = {
  login: async (organization: string, username: string, password: string) =>
    (await api.post<TokenResponse>("/auth/login", { organization, username, password })).data,
  register: async (payload: {
    organization_name: string;
    industry?: string;
    username: string;
    email: string;
    password: string;
  }) => (await api.post<TokenResponse>("/auth/register", payload)).data,
  me: async () => (await api.get<AuthUser>("/auth/me")).data,
  refresh: async (refreshToken: string) =>
    (await api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })).data,
  logout: async (refreshToken: string) =>
    api.post("/auth/logout", { refresh_token: refreshToken }),
};

export const usersApi = {
  list: async () => (await api.get<AuthUser[]>("/users")).data,
  create: async (payload: { username: string; email: string; password: string; role: UserRole }) =>
    (await api.post<AuthUser>("/users", payload)).data,
};

export const enterpriseApi = {
  overview: async () => (await api.get<EnterpriseOverview>("/enterprise/overview")).data,
  organization: async () => (await api.get<Organization>("/organizations/current")).data,
  users: async () => (await api.get<AuthUser[]>("/users")).data,
  audit: async () => (await api.get<AuditLog[]>("/audit-logs")).data,
  health: async () => (await axios.get<FullHealth>(`${apiOrigin}/health/full`)).data,
  report: async (type: ReportType, format: ReportFormat) =>
    (
      await api.get<Blob>(`/reports/${type}`, {
        params: { format },
        responseType: "blob",
      })
    ).data,
};

export const benchmarksApi = {
  pqc: async () => (await api.get<BenchmarkCatalogue>("/benchmarks/pqc")).data,
  run: async (iterations: number) =>
    (await api.post<BenchmarkCatalogue>("/benchmarks/run", { iterations, include_pqc: true })).data,
  migrationImpact: async (query: MigrationImpactQuery) =>
    (await api.get<MigrationImpact>("/benchmarks/migration-impact", { params: query })).data,
};

export const validationApi = {
  migrations: async (projectId?: string) =>
    (
      await api.get<MigrationVerificationReport>("/analytics/validation/migrations", {
        params: { project_id: projectId },
      })
    ).data,
  baseline: async () => (await api.get<ValidationEnvelope>("/analytics/validation")).data,
};

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: string } | undefined;
    return detail?.detail ?? error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

/** Report downloads use `responseType: "blob"`, so a server error arrives as a Blob of JSON. */
export async function apiReportErrorMessage(error: unknown): Promise<string> {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      const parsed = JSON.parse(await error.response.data.text()) as { detail?: string };
      if (parsed.detail) return parsed.detail;
    } catch {
      // Not JSON: fall back to the status-based message below.
    }
    if (error.response.status === 403) return "Your role is not allowed to export reports.";
  }
  return apiErrorMessage(error);
}
