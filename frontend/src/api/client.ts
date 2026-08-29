import axios from "axios";
import type {
  AssetPage,
  Criticality,
  DashboardData,
  GraphData,
  BlastRadiusData,
  IntelligenceRiskData,
  MigrationRecommendation,
  MigrationRoadmap,
  RiskPage,
  Scan,
} from "../types/api";

const apiOrigin = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const apiBaseUrl = apiOrigin.endsWith("/api/v1") ? apiOrigin : `${apiOrigin}/api/v1`;
const phase2BaseUrl = apiOrigin.endsWith("/api/v1")
  ? apiOrigin.replace(/\/api\/v1$/, "/api")
  : `${apiOrigin}/api`;

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60_000,
  headers: { Accept: "application/json" },
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
    (await axios.get<IntelligenceRiskData>(`${phase2BaseUrl}/intelligence/risk`)).data,
  hndl: async () =>
    (await axios.get<{ total: number; items: IntelligenceRiskData["items"] }>(`${phase2BaseUrl}/intelligence/hndl`)).data,
  blastRadius: async (assetId?: string) =>
    (await axios.get<BlastRadiusData>(`${phase2BaseUrl}/intelligence/blast-radius`, { params: { asset_id: assetId } })).data,
};

export const migrationApi = {
  recommendations: async () =>
    (await axios.get<MigrationRecommendation[]>(`${phase2BaseUrl}/migration/recommendations`)).data,
  roadmap: async () =>
    (await axios.get<MigrationRoadmap>(`${phase2BaseUrl}/migration/roadmap`)).data,
};

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: string } | undefined;
    return detail?.detail ?? error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}
