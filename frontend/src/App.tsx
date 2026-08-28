import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/ui";

const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const UploadCenter = lazy(() => import("./pages/UploadCenter").then((module) => ({ default: module.UploadCenter })));
const AssetExplorer = lazy(() => import("./pages/AssetExplorer").then((module) => ({ default: module.AssetExplorer })));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph").then((module) => ({ default: module.KnowledgeGraph })));
const RiskAnalysis = lazy(() => import("./pages/RiskAnalysis").then((module) => ({ default: module.RiskAnalysis })));
const NotFound = lazy(() => import("./pages/NotFound").then((module) => ({ default: module.NotFound })));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="min-h-screen bg-ink-950"><LoadingState /></div>}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<UploadCenter />} />
            <Route path="assets" element={<AssetExplorer />} />
            <Route path="graph" element={<KnowledgeGraph />} />
            <Route path="risks" element={<RiskAnalysis />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
