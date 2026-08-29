import { Activity, Boxes, KeyRound, ShieldAlert, TriangleAlert, Upload } from "lucide-react";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart, CartesianGrid } from "recharts";
import { Link } from "react-router-dom";
import { apiErrorMessage, dashboardApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { formatNumber, relativeTime } from "../utils/format";

const riskColors: Record<string, string> = {
  critical: "#fb7185",
  high: "#fb923c",
  medium: "#facc15",
  low: "#34d399",
};

export function Dashboard() {
  const { data, error, loading, reload } = useAsync(dashboardApi.get, []);
  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const metrics = [
    { label: "Total crypto assets", value: data.metrics.total_assets, icon: Boxes, accent: "text-brand-300", surface: "bg-brand-400/10" },
    { label: "Critical assets", value: data.metrics.critical_assets, icon: ShieldAlert, accent: "text-rose-300", surface: "bg-rose-400/10" },
    { label: "High-risk assets", value: data.metrics.high_assets, icon: TriangleAlert, accent: "text-orange-300", surface: "bg-orange-400/10" },
    { label: "Algorithms found", value: data.metrics.algorithms_found, icon: KeyRound, accent: "text-violet-300", surface: "bg-violet-400/10" },
  ];
  const riskTotal = data.risk_distribution.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Security posture"
        title="Cryptographic risk overview"
        description="A live inventory of cryptographic dependencies, exposure, and migration pressure across your enterprise estate."
        action={
          <Link to="/upload" className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-400 px-4 py-2.5 text-sm font-bold text-ink-950 shadow-glow transition hover:bg-brand-300">
            <Upload className="h-4 w-4" /> Start a scan
          </Link>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon, accent, surface }) => (
          <Card key={label} className="group relative overflow-hidden p-5 transition hover:-translate-y-0.5 hover:border-white/10">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">{label}</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{formatNumber(value)}</p>
              </div>
              <span className={`rounded-xl p-2.5 ${surface} ${accent}`}><Icon className="h-5 w-5" /></span>
            </div>
            <div className="mt-5 flex items-center gap-2 text-[11px] text-slate-600">
              <Activity className="h-3.5 w-3.5 text-slate-500" /> Current discovery inventory
            </div>
          </Card>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.85fr_1.4fr]">
        <Card className="p-5 md:p-6">
          <div>
            <p className="text-sm font-semibold text-white">Risk distribution</p>
            <p className="mt-1 text-xs text-slate-500">Explainable severity across inventoried assets</p>
          </div>
          {riskTotal ? (
            <div className="relative mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.risk_distribution} dataKey="value" nameKey="name" innerRadius={72} outerRadius={102} paddingAngle={3} stroke="none">
                    {data.risk_distribution.map((item) => <Cell key={item.name} fill={riskColors[item.name] ?? "#64748b"} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} />
                  <Legend iconType="circle" formatter={(value) => <span className="capitalize text-slate-400">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute left-1/2 top-[44%] -translate-x-1/2 -translate-y-1/2 text-center">
                <p className="text-3xl font-semibold text-white">{riskTotal}</p><p className="text-[10px] uppercase tracking-widest text-slate-500">scored</p>
              </div>
            </div>
          ) : <EmptyState title="No scored assets" body="Run a scan to populate the risk model." />}
        </Card>

        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-white">Algorithm distribution</p>
          <p className="mt-1 text-xs text-slate-500">Most prevalent cryptographic primitives</p>
          {data.algorithm_distribution.length ? (
            <div className="mt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.algorithm_distribution} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="rgba(148,163,184,.08)" />
                  <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "rgba(34,211,238,.04)" }} contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} />
                  <Bar dataKey="value" name="Assets" fill="#22d3ee" radius={[6, 6, 0, 0]} maxBarSize={44} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyState title="No algorithms discovered" body="Algorithm distribution appears after the first completed scan." />}
        </Card>
      </section>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4 md:px-6">
          <div><p className="text-sm font-semibold text-white">Recent scan activity</p><p className="mt-1 text-xs text-slate-500">Latest discovery jobs across all sources</p></div>
          <Link to="/upload" className="text-xs font-semibold text-brand-300 hover:text-brand-200">View upload center</Link>
        </div>
        {data.recent_scans.length ? (
          <div className="divide-y divide-white/[0.05]">
            {data.recent_scans.map((scan) => (
              <div key={scan.id} className="grid gap-3 px-5 py-4 text-sm transition hover:bg-white/[0.02] md:grid-cols-[1fr_180px_120px_120px] md:items-center md:px-6">
                <div className="min-w-0"><p className="truncate font-medium text-slate-200">{scan.target}</p><p className="mt-1 text-xs capitalize text-slate-600">{scan.source_type} discovery</p></div>
                <p className="text-xs text-slate-500">{(scan.summary.assets_discovered as number | undefined) ?? 0} assets found</p>
                <StatusBadge status={scan.status} />
                <p className="text-xs text-slate-600 md:text-right">{relativeTime(scan.completed_at ?? scan.created_at)}</p>
              </div>
            ))}
          </div>
        ) : <EmptyState title="No scan activity" body="Upload a repository or provide an infrastructure target to begin." />}
      </Card>
    </div>
  );
}
