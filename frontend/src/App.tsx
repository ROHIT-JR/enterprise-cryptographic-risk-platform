import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/ui";

const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const UploadCenter = lazy(() => import("./pages/UploadCenter").then((module) => ({ default: module.UploadCenter })));
const AssetExplorer = lazy(() => import("./pages/AssetExplorer").then((module) => ({ default: module.AssetExplorer })));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph").then((module) => ({ default: module.KnowledgeGraph })));
const RiskAnalysis = lazy(() => import("./pages/RiskAnalysis").then((module) => ({ default: module.RiskAnalysis })));
const QuantumRiskDashboard = lazy(() => import("./pages/QuantumRiskDashboard").then((module) => ({ default: module.QuantumRiskDashboard })));
const AssetIntelligence = lazy(() => import("./pages/AssetIntelligence").then((module) => ({ default: module.AssetIntelligence })));
const BlastRadius = lazy(() => import("./pages/BlastRadius").then((module) => ({ default: module.BlastRadius })));
const MigrationPlanner = lazy(() => import("./pages/MigrationPlanner").then((module) => ({ default: module.MigrationPlanner })));
const PQCRecommendations = lazy(() => import("./pages/PQCRecommendations").then((module) => ({ default: module.PQCRecommendations })));
const PQCBenchmarks = lazy(() => import("./pages/PQCBenchmarks").then((module) => ({ default: module.PQCBenchmarks })));
const Login = lazy(() => import("./pages/Login").then((module) => ({ default: module.Login })));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard").then((module) => ({ default: module.AdminDashboard })));
const SecurityOperations = lazy(() => import("./pages/SecurityOperations").then((module) => ({ default: module.SecurityOperations })));
const AuditorView = lazy(() => import("./pages/AuditorView").then((module) => ({ default: module.AuditorView })));
const ValidationDashboard = lazy(() => import("./pages/ValidationDashboard").then((module) => ({ default: module.ValidationDashboard })));
const NotFound = lazy(() => import("./pages/NotFound").then((module) => ({ default: module.NotFound })));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<div className="min-h-screen bg-ink-950"><LoadingState /></div>}>
          <Routes>
            <Route path="login" element={<Login />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<UploadCenter />} />
            <Route path="assets" element={<AssetExplorer />} />
            <Route path="graph" element={<KnowledgeGraph />} />
            <Route path="risks" element={<RiskAnalysis />} />
            <Route path="quantum-risk" element={<QuantumRiskDashboard />} />
            <Route path="intelligence" element={<AssetIntelligence />} />
            <Route path="blast-radius" element={<BlastRadius />} />
            <Route path="migration" element={<MigrationPlanner />} />
            <Route path="pqc" element={<PQCRecommendations />} />
            <Route path="benchmarks" element={<PQCBenchmarks />} />
            <Route path="admin" element={<AdminDashboard />} />
            <Route path="operations" element={<SecurityOperations />} />
            <Route path="audit" element={<AuditorView />} />
            <Route path="validation" element={<ValidationDashboard />} />
            <Route path="*" element={<NotFound />} />
              </Route>
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
