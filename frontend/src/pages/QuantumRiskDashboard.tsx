import { Activity, Atom, DatabaseZap, ShieldAlert } from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SeverityBadge,
} from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { IntelligenceItem } from "../types/api";

const colors: Record<string, string> = {
  critical: "#ef4444",
  high:     "#f97316",
  medium:   "#f59e0b",
  low:      "#22c55e",
  secure:   "#3b82f6",
  unknown:  "#94a3b8",
};

const CURRENT_YEAR = new Date().getFullYear();

// Derive data sensitivity label from hndl_risk
function sensitivityLabel(item: IntelligenceItem): string {
  if (item.hndl_risk === "critical") return "Top Secret";
  if (item.hndl_risk === "high")     return "Confidential";
  if (item.hndl_risk === "medium")   return "Sensitive";
  return "Internal";
}

// Estimate data lifetime (years) from hndl_score (0-100 → 0-30 years proxy)
function estimateDataLifetime(item: IntelligenceItem): number {
  return Math.round((item.hndl_score / 100) * 25) + 3;
}

// ─────────────────────────────────────────────
// HNDL Timeline component
// ─────────────────────────────────────────────
function HndlTimeline({ quantumYear }: { quantumYear: number }) {
  const timeToQuantum = quantumYear - CURRENT_YEAR;
  const totalSpan = 2045 - CURRENT_YEAR;
  const markerPct = Math.round(((quantumYear - CURRENT_YEAR) / totalSpan) * 100);

  return (
    <Card className="p-6">
      <p className="mb-1 text-base font-semibold text-slate-900">HNDL Threat Timeline</p>
      <p className="mb-5 text-xs text-slate-500">
        Adversaries harvest encrypted data today to decrypt it once quantum computers arrive. Adjust the slider to estimate quantum arrival timing.
      </p>

      {/* Timeline bar */}
      <div className="relative h-16 rounded-xl border border-slate-200 bg-slate-50 overflow-hidden">
        {/* Zones */}
        <div
          className="absolute inset-y-0 left-0 flex items-center justify-center border-r border-red-200 bg-red-50/80 transition-all duration-200"
          style={{ width: `${markerPct}%` }}
        >
          <div className="flex items-center gap-2 px-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-data-packet h-2.5 w-4 rounded-sm bg-red-400"
                style={{ animationDelay: `${i * 0.8}s` }}
              />
            ))}
            <span className="hidden text-[11px] font-medium text-red-700 sm:block">
              Harvesting window
            </span>
          </div>
        </div>
        <div
          className="absolute inset-y-0 right-0 flex items-center justify-center bg-amber-50/70 transition-all duration-200"
          style={{ width: `${100 - markerPct}%` }}
        >
          <div className="flex items-center gap-2 px-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-decrypt h-2.5 w-4 rounded-sm bg-amber-400"
                style={{ animationDelay: `${i * 0.6 + 1}s` }}
              />
            ))}
            <span className="hidden text-[11px] font-medium text-amber-800 sm:block">
              Decryption era
            </span>
          </div>
        </div>

        {/* Quantum arrival marker line */}
        <div
          className="absolute inset-y-0 z-10 flex flex-col items-center"
          style={{ left: `${markerPct}%`, transform: "translateX(-50%)" }}
        >
          <div className="h-full w-px border-l-2 border-dashed border-indigo-500" />
          <div className="absolute top-1.5 flex items-center gap-1 whitespace-nowrap rounded-md border border-indigo-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-indigo-700 shadow-sm">
            Q-Day {quantumYear}
          </div>
        </div>
      </div>

      {/* Year labels */}
      <div className="mt-2 flex justify-between text-xs text-slate-400">
        <span>{CURRENT_YEAR} (Today)</span>
        <span className="font-semibold text-indigo-600">Estimated Q-Day: {quantumYear}</span>
        <span>2045</span>
      </div>

      {/* Time indicators */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          {timeToQuantum} years until Q-day — active data retention is exposed
        </div>
        <div className="flex items-center gap-1.5 ml-auto text-slate-400">
          Slide below to evaluate different arrival scenarios
        </div>
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────
// HNDL Asset Card
// ─────────────────────────────────────────────
function HndlAssetCard({ item, quantumYear }: { item: IntelligenceItem; quantumYear: number }) {
  const timeToQuantum = quantumYear - CURRENT_YEAR;
  const dataLifetime = estimateDataLifetime(item);
  const isAtRisk = dataLifetime > timeToQuantum;
  const sensitivity = sensitivityLabel(item);

  return (
    <Card className={`p-4 transition ${
      isAtRisk
        ? "border-red-200 bg-red-50/20"
        : "border-slate-200 bg-white"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{item.asset_name}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {item.algorithm ?? item.asset_type} · {item.project_name}
          </p>
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] ${
          isAtRisk
            ? "border-red-200 bg-red-50 text-red-700"
            : "border-green-200 bg-green-50 text-green-700"
        }`}>
          {isAtRisk ? "At Risk" : "Safe"}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
          <p className="text-slate-400">Data sensitivity</p>
          <p className="mt-0.5 font-semibold text-slate-800">{sensitivity}</p>
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
          <p className="text-slate-400">Est. data lifetime</p>
          <p className="mt-0.5 font-semibold text-slate-800">{dataLifetime} years</p>
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
          <p className="text-slate-400">Time to Q-day</p>
          <p className={`mt-0.5 font-semibold ${isAtRisk ? "text-red-600" : "text-emerald-600"}`}>
            {timeToQuantum} years
          </p>
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
          <p className="text-slate-400">HNDL score</p>
          <p className="mt-0.5 font-semibold text-slate-800">{Math.round(item.hndl_score)}/100</p>
        </div>
      </div>
      {isAtRisk && (
        <p className="mt-2.5 text-[11px] text-red-600">
          Harvested today could be decrypted in {timeToQuantum} years — before its {dataLifetime}-year retention expires.
        </p>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────
export function QuantumRiskDashboard() {
  const { data, error, loading, reload } = useAsync(intelligenceApi.risk, []);
  const [quantumYear, setQuantumYear] = useState(2032);

  if (loading) return <LoadingState label="Calculating quantum risk intelligence" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const metrics = [
    { label: "Vulnerable assets",    value: data.metrics.vulnerable_assets,       icon: Atom,        color: "text-indigo-600", bg: "bg-indigo-50" },
    { label: "Critical quantum risks", value: data.metrics.critical_quantum_risks, icon: ShieldAlert, color: "text-red-600",    bg: "bg-red-50" },
    { label: "HNDL exposures",       value: data.metrics.hndl_exposures,           icon: DatabaseZap, color: "text-amber-600",  bg: "bg-amber-50" },
    { label: "Average risk score",   value: data.metrics.average_risk_score,       icon: Activity,    color: "text-blue-600",   bg: "bg-blue-50" },
  ];

  const atRiskCount = data.items.filter(
    (item) => estimateDataLifetime(item) > (quantumYear - CURRENT_YEAR),
  ).length;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Phase 2 intelligence"
        title="Quantum risk dashboard"
        description="Prioritize cryptographic exposure using quantum vulnerability, HNDL, blast radius, business impact, migration complexity, and evidence confidence."
      />

      {/* Metrics row */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon, color, bg }) => (
          <Card key={label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="tabular-nums mt-2.5 text-3xl font-semibold text-slate-900">{value}</p>
              </div>
              <span className={`rounded-lg p-2.5 ${bg} ${color}`}><Icon className="h-5 w-5" /></span>
            </div>
          </Card>
        ))}
      </section>

      {/* HNDL Timeline */}
      <section className="space-y-4">
        <HndlTimeline quantumYear={quantumYear} />
        {/* Slider Card */}
        <Card className="p-4 flex flex-col sm:flex-row items-center gap-4">
          <span className="text-xs font-medium text-slate-600 shrink-0">Adjust Q-Day Target:</span>
          <input
            type="range"
            min={2028}
            max={2045}
            value={quantumYear}
            onChange={(e) => setQuantumYear(Number(e.target.value))}
            className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-blue-600"
          />
          <span className="tabular-nums shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-800">
            {quantumYear}
          </span>
        </Card>
        <p className="text-xs text-slate-500 px-1">
          {atRiskCount} of {data.items.length} analyzed assets are exposed to Harvest Now, Decrypt Later threats based on a Q-Day of {quantumYear}.
        </p>
      </section>

      {/* Charts */}
      <section className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-slate-900">Algorithm vulnerability</p>
          <p className="mt-1 text-xs text-slate-400">Quantum classification across discovered cryptography</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.algorithm_vulnerability_distribution}>
                <CartesianGrid vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 10, fontSize: 12 }} />
                <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={44} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-slate-900">Final risk severity</p>
          <p className="mt-1 text-xs text-slate-400">Normalized ECDAT score from six intelligence factors</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.severity_distribution} dataKey="value" nameKey="name" innerRadius={68} outerRadius={105} paddingAngle={3} stroke="none">
                  {data.severity_distribution.map((item) => (
                    <Cell key={item.name} fill={colors[item.name] ?? "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 10, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Per-asset HNDL risk cards */}
      {data.items.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Per-asset HNDL risk</p>
            <span className="text-xs text-slate-500">
              Q-Day: <span className="font-semibold text-indigo-600">{quantumYear}</span>
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((item) => (
              <HndlAssetCard key={item.asset_id} item={item} quantumYear={quantumYear} />
            ))}
          </div>
        </section>
      )}

      {/* Highest-priority assets table */}
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <p className="text-sm font-semibold text-slate-900">Highest-priority assets</p>
        </div>
        {data.items.length ? (
          <div className="divide-y divide-slate-100">
            {data.items.slice(0, 6).map((item) => (
              <div key={item.asset_id} className="grid gap-3 px-5 py-4 transition hover:bg-slate-50 md:grid-cols-[1fr_140px_140px_120px] md:items-center">
                <div>
                  <p className="text-sm font-medium text-slate-900">{item.asset_name}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.algorithm ?? item.asset_type} · {item.dependent_systems} affected systems</p>
                </div>
                <p className="text-xs text-slate-500">HNDL <span className="font-medium capitalize text-amber-700">{item.hndl_risk}</span></p>
                <p className="text-xs text-slate-500">Confidence <span className="font-medium text-blue-600">{item.evidence_confidence}%</span></p>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={item.severity} />
                  <span className="tabular-nums font-mono text-sm font-semibold text-slate-800">{Math.round(item.final_score)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No intelligence yet" body="Complete a discovery scan to calculate Phase 2 risk." />
        )}
      </Card>
    </div>
  );
}
