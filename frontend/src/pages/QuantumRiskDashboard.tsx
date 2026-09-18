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
  medium:   "#eab308",
  low:      "#22c55e",
  secure:   "#22d3ee",
  unknown:  "#64748b",
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
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-ink-900/60 p-6">
      <p className="mb-1 text-sm font-semibold text-white">HNDL Threat Timeline</p>
      <p className="mb-5 text-xs text-slate-500">
        Adversaries harvest encrypted data today to decrypt it once quantum computers arrive. Move the slider to change the assumed quantum arrival year.
      </p>

      {/* Timeline bar */}
      <div className="relative h-16">
        {/* Zones */}
        <div
          className="absolute inset-y-0 left-0 flex items-center justify-center rounded-l-xl bg-rose-500/10 border border-rose-500/20"
          style={{ width: `${markerPct}%` }}
        >
          <div className="flex items-center gap-2 px-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-data-packet h-3 w-5 rounded-sm bg-rose-400/70"
                style={{ animationDelay: `${i * 0.8}s` }}
              />
            ))}
            <span className="hidden text-[10px] font-semibold text-rose-300 sm:block">
              Data being harvested
            </span>
          </div>
        </div>
        <div
          className="absolute inset-y-0 right-0 flex items-center justify-center rounded-r-xl bg-amber-500/10 border border-amber-500/20"
          style={{ width: `${100 - markerPct}%` }}
        >
          <div className="flex items-center gap-2 px-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-decrypt h-3 w-5 rounded-sm bg-amber-400/70"
                style={{ animationDelay: `${i * 0.6 + 1}s` }}
              />
            ))}
            <span className="hidden text-[10px] font-semibold text-amber-300 sm:block">
              Data decrypted
            </span>
          </div>
        </div>

        {/* Quantum arrival marker line */}
        <div
          className="absolute inset-y-0 z-10 flex flex-col items-center"
          style={{ left: `${markerPct}%`, transform: "translateX(-50%)" }}
        >
          <div className="h-full w-px border-l-2 border-dashed border-violet-400/70" />
          <div className="absolute top-1 flex items-center gap-1 whitespace-nowrap rounded-full border border-violet-400/30 bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold text-violet-300">
            ⚡ {quantumYear}
          </div>
        </div>
      </div>

      {/* Year labels */}
      <div className="mt-2 flex justify-between text-[10px] text-slate-600">
        <span>{CURRENT_YEAR}</span>
        <span className="font-semibold text-violet-400">Q-Day: {quantumYear}</span>
        <span>2045</span>
      </div>

      {/* Time indicators */}
      <div className="mt-4 flex gap-4 text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-rose-400" />
          {timeToQuantum} years until Q-day — data harvested NOW is at risk
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="h-2 w-2 rounded-full bg-violet-400" />
          Slide to adjust quantum arrival year
        </div>
      </div>
    </div>
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
    <div className={`rounded-xl border p-4 transition ${
      isAtRisk
        ? "border-rose-500/25 bg-rose-500/[0.06]"
        : "border-emerald-500/20 bg-emerald-500/[0.04]"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">{item.asset_name}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {item.algorithm ?? item.asset_type} · {item.project_name}
          </p>
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${
          isAtRisk
            ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
            : "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
        }`}>
          {isAtRisk ? "⚠ At Risk" : "✓ Safe"}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-white/[0.025] px-3 py-2">
          <p className="text-slate-500">Data sensitivity</p>
          <p className="mt-0.5 font-semibold text-slate-200">{sensitivity}</p>
        </div>
        <div className="rounded-lg bg-white/[0.025] px-3 py-2">
          <p className="text-slate-500">Est. data lifetime</p>
          <p className="mt-0.5 font-semibold text-slate-200">{dataLifetime} years</p>
        </div>
        <div className="rounded-lg bg-white/[0.025] px-3 py-2">
          <p className="text-slate-500">Time to Q-day</p>
          <p className={`mt-0.5 font-semibold ${isAtRisk ? "text-rose-300" : "text-emerald-300"}`}>
            {timeToQuantum} years
          </p>
        </div>
        <div className="rounded-lg bg-white/[0.025] px-3 py-2">
          <p className="text-slate-500">HNDL score</p>
          <p className="mt-0.5 font-semibold text-slate-200">{Math.round(item.hndl_score)}/100</p>
        </div>
      </div>
      {isAtRisk && (
        <p className="mt-3 text-[11px] text-rose-300">
          ⚠ Data harvested today could be decrypted in {timeToQuantum} years — before its {dataLifetime}-year lifetime expires.
        </p>
      )}
    </div>
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
    { label: "Vulnerable assets",    value: data.metrics.vulnerable_assets,       icon: Atom,        color: "text-violet-300", bg: "bg-violet-400/10" },
    { label: "Critical quantum risks", value: data.metrics.critical_quantum_risks, icon: ShieldAlert, color: "text-rose-300",   bg: "bg-rose-400/10" },
    { label: "HNDL exposures",       value: data.metrics.hndl_exposures,           icon: DatabaseZap, color: "text-orange-300", bg: "bg-orange-400/10" },
    { label: "Average risk score",   value: data.metrics.average_risk_score,       icon: Activity,    color: "text-brand-300",  bg: "bg-brand-400/10" },
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
                <p className="tabular-nums mt-3 text-3xl font-semibold text-white">{value}</p>
              </div>
              <span className={`rounded-xl p-2.5 ${bg} ${color}`}><Icon className="h-5 w-5" /></span>
            </div>
          </Card>
        ))}
      </section>

      {/* HNDL Timeline */}
      <section>
        <HndlTimeline quantumYear={quantumYear} />
        {/* Slider */}
        <div className="mt-4 flex items-center gap-4">
          <span className="text-xs text-slate-500 shrink-0">Q-Day estimate:</span>
          <input
            type="range"
            min={2028}
            max={2045}
            value={quantumYear}
            onChange={(e) => setQuantumYear(Number(e.target.value))}
            className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-ink-750 accent-violet-500"
          />
          <span className="tabular-nums shrink-0 rounded-full border border-violet-400/25 bg-violet-500/10 px-3 py-1 text-xs font-bold text-violet-300">
            {quantumYear}
          </span>
        </div>
        <p className="mt-2 text-[11px] text-slate-600">
          {atRiskCount} of {data.items.length} analyzed assets are at HNDL risk at Q-Day {quantumYear}
        </p>
      </section>

      {/* Charts */}
      <section className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-white">Algorithm vulnerability</p>
          <p className="mt-1 text-xs text-slate-500">Quantum classification across discovered cryptography</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.algorithm_vulnerability_distribution}>
                <CartesianGrid vertical={false} stroke="rgba(148,163,184,.08)" />
                <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} itemStyle={{ color: "#e2e8f0" }} />
                <Bar dataKey="value" fill="#a78bfa" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-white">Final risk severity</p>
          <p className="mt-1 text-xs text-slate-500">Normalized ECDAT score from six intelligence factors</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.severity_distribution} dataKey="value" nameKey="name" innerRadius={68} outerRadius={105} paddingAngle={3} stroke="none">
                  {data.severity_distribution.map((item) => (
                    <Cell key={item.name} fill={colors[item.name] ?? "#64748b"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} itemStyle={{ color: "#e2e8f0" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Per-asset HNDL risk cards */}
      {data.items.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-600">Per-asset HNDL risk</p>
            <span className="text-xs text-slate-500">
              Q-Day: <span className="font-semibold text-violet-300">{quantumYear}</span>
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
        <div className="border-b border-white/[0.06] px-5 py-4">
          <p className="text-sm font-semibold text-white">Highest-priority assets</p>
        </div>
        {data.items.length ? (
          <div className="divide-y divide-white/[0.05]">
            {data.items.slice(0, 6).map((item) => (
              <div key={item.asset_id} className="grid gap-3 px-5 py-4 md:grid-cols-[1fr_140px_140px_120px] md:items-center">
                <div>
                  <p className="text-sm font-medium text-slate-100">{item.asset_name}</p>
                  <p className="mt-1 text-xs text-slate-600">{item.algorithm ?? item.asset_type} · {item.dependent_systems} affected systems</p>
                </div>
                <p className="text-xs text-slate-400">HNDL <span className="capitalize text-orange-300">{item.hndl_risk}</span></p>
                <p className="text-xs text-slate-400">Confidence <span className="text-brand-300">{item.evidence_confidence}%</span></p>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={item.severity} />
                  <span className="tabular-nums font-mono text-sm text-white">{Math.round(item.final_score)}</span>
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
