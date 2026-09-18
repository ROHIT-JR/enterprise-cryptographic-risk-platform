import {
  Activity,
  Atom,
  Boxes,
  ChevronRight,
  CircleDotDashed,
  FileDown,
  KeyRound,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  BarChart,
  CartesianGrid,
} from "recharts";
import { Link } from "react-router-dom";
import { apiErrorMessage, dashboardApi, enterpriseApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { formatNumber, relativeTime } from "../utils/format";

const riskColors: Record<string, string> = {
  critical: "#ef4444",
  high:     "#f97316",
  medium:   "#eab308",
  low:      "#22c55e",
};

function QuickActionButton({
  to,
  icon: Icon,
  label,
  description,
  accent,
}: {
  to?: string;
  icon: React.ElementType;
  label: string;
  description: string;
  accent: string;
  onClick?: () => void;
}) {
  const inner = (
    <Card className="group flex items-center gap-4 p-4 transition hover:-translate-y-0.5 hover:border-white/10 cursor-pointer">
      <span className={`shrink-0 rounded-xl p-2.5 ${accent}`}>
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="mt-0.5 truncate text-xs text-slate-500">{description}</p>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-600 transition group-hover:text-slate-400" />
    </Card>
  );
  return to ? <Link to={to}>{inner}</Link> : inner;
}

async function downloadReport() {
  try {
    const blob = await enterpriseApi.report("inventory", "json");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ecdat-inventory-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    // Silently fail if backend not available — don't crash the page
  }
}

export function Dashboard() {
  const { data, error, loading, reload } = useAsync(dashboardApi.get, []);
  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  // Derive quantum exposure: use backend value if present, else compute proxy from critical/total
  const quantumExposure =
    data.metrics.quantum_exposure_percent != null
      ? `${data.metrics.quantum_exposure_percent}%`
      : data.metrics.total_assets > 0
        ? `${Math.round((data.metrics.critical_assets / data.metrics.total_assets) * 100)}%`
        : "—";

  // Overall risk score: use backend value if present
  const overallRiskScore =
    data.metrics.average_risk_score != null
      ? Math.round(data.metrics.average_risk_score)
      : "—";

  const metrics = [
    {
      label:   "Total Assets Discovered",
      value:   formatNumber(data.metrics.total_assets),
      icon:    Boxes,
      accent:  "text-brand-300",
      surface: "bg-brand-400/10",
      sub:     `${data.metrics.projects_scanned} project${data.metrics.projects_scanned !== 1 ? "s" : ""} scanned`,
    },
    {
      label:   "Critical Findings",
      value:   formatNumber(data.metrics.critical_assets),
      icon:    ShieldAlert,
      accent:  "text-rose-300",
      surface: "bg-rose-500/10",
      sub:     "Require immediate action",
    },
    {
      label:   "Quantum Exposure",
      value:   quantumExposure,
      icon:    Atom,
      accent:  "text-violet-300",
      surface: "bg-violet-500/10",
      sub:     "Assets with vulnerable algorithms",
    },
    {
      label:   "Overall Risk Score",
      value:   overallRiskScore,
      icon:    Activity,
      accent:  "text-amber-300",
      surface: "bg-amber-500/10",
      sub:     `${formatNumber(data.metrics.algorithms_found)} algorithms discovered`,
    },
  ];

  const riskTotal = data.risk_distribution.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Security posture"
        title="Cryptographic risk overview"
        description="A live inventory of cryptographic dependencies, exposure, and migration pressure across your enterprise estate."
        action={
          <Link
            to="/upload"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-400 px-4 py-2.5 text-sm font-bold text-ink-950 shadow-glow transition hover:bg-brand-300"
          >
            <ScanLine className="h-4 w-4" /> Start a scan
          </Link>
        }
      />

      {/* Hero stats row */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon, accent, surface, sub }) => (
          <Card key={label} className="group relative overflow-hidden p-5 transition hover:-translate-y-0.5 hover:border-white/10">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">{label}</p>
                <p className="tabular-nums mt-3 text-3xl font-semibold tracking-tight text-white">{value}</p>
              </div>
              <span className={`rounded-xl p-2.5 ${surface} ${accent}`}>
                <Icon className="h-5 w-5" />
              </span>
            </div>
            <div className="mt-4 flex items-center gap-1.5 text-[11px] text-slate-600">
              <Activity className="h-3 w-3 text-slate-500" />
              {sub}
            </div>
          </Card>
        ))}
      </section>

      {/* Quick actions */}
      <section>
        <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-600">Quick actions</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <QuickActionButton
            to="/upload"
            icon={ScanLine}
            label="Scan Repository"
            description="Upload a ZIP or point to a Docker image"
            accent="text-brand-300 bg-brand-400/10"
          />
          <QuickActionButton
            to="/blast-radius"
            icon={CircleDotDashed}
            label="View Blast Radius"
            description="Simulate crypto asset compromise impact"
            accent="text-rose-300 bg-rose-500/10"
          />
          <QuickActionButton
            icon={FileDown}
            label="Generate Report"
            description="Download full inventory as JSON"
            accent="text-violet-300 bg-violet-500/10"
            onClick={() => void downloadReport()}
          />
        </div>
      </section>

      {/* Charts */}
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
                  <Pie
                    data={data.risk_distribution}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={72}
                    outerRadius={102}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {data.risk_distribution.map((item) => (
                      <Cell key={item.name} fill={riskColors[item.name] ?? "#64748b"} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }}
                    itemStyle={{ color: "#e2e8f0" }}
                  />
                  <Legend iconType="circle" formatter={(value) => <span className="capitalize text-slate-400">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute left-1/2 top-[44%] -translate-x-1/2 -translate-y-1/2 text-center">
                <p className="tabular-nums text-3xl font-semibold text-white">{riskTotal}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">scored</p>
              </div>
            </div>
          ) : (
            <EmptyState title="No scored assets" body="Run a scan to populate the risk model." />
          )}
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
                  <Tooltip
                    cursor={{ fill: "rgba(34,211,238,.04)" }}
                    contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }}
                    itemStyle={{ color: "#e2e8f0" }}
                  />
                  <Bar dataKey="value" name="Assets" fill="#22d3ee" radius={[6, 6, 0, 0]} maxBarSize={44} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No algorithms discovered" body="Algorithm distribution appears after the first completed scan." />
          )}
        </Card>
      </section>

      {/* Recent scans */}
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4 md:px-6">
          <div>
            <p className="text-sm font-semibold text-white">Recent scan activity</p>
            <p className="mt-1 text-xs text-slate-500">Latest discovery jobs across all sources</p>
          </div>
          <Link to="/upload" className="text-xs font-semibold text-brand-300 hover:text-brand-200">
            View all scans →
          </Link>
        </div>
        {data.recent_scans.length ? (
          <div className="divide-y divide-white/[0.05]">
            {data.recent_scans.slice(0, 5).map((scan) => (
              <div
                key={scan.id}
                className="grid gap-3 px-5 py-4 text-sm transition hover:bg-white/[0.02] md:grid-cols-[1fr_180px_120px_120px] md:items-center md:px-6"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-200">{scan.target}</p>
                  <p className="mt-1 text-xs capitalize text-slate-600">{scan.source_type} discovery</p>
                </div>
                <p className="text-xs text-slate-500">
                  {(scan.summary.assets_discovered as number | undefined) ?? 0} assets found
                </p>
                <StatusBadge status={scan.status} />
                <p className="text-xs text-slate-600 md:text-right">
                  {relativeTime(scan.completed_at ?? scan.created_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No scan activity"
            body="Upload a repository or provide an infrastructure target to begin."
          />
        )}
      </Card>
    </div>
  );
}
