import {
  Activity,
  Atom,
  Boxes,
  ChevronRight,
  CircleDotDashed,
  FileDown,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
import {
  Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip,
  XAxis, YAxis, Bar, BarChart, CartesianGrid,
} from "recharts";
import { Link } from "react-router-dom";
import { apiErrorMessage, dashboardApi, enterpriseApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { formatNumber, relativeTime } from "../utils/format";

const riskColors: Record<string, string> = {
  critical: "#ef4444",
  high:     "#f97316",
  medium:   "#f59e0b",
  low:      "#22c55e",
};

const TOOLTIP_STYLE = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  color: "#0f172a",
  fontSize: 12,
};

function QuickActionButton({
  to,
  icon: Icon,
  label,
  description,
  iconClass,
  iconBg,
  onClick,
}: {
  to?: string;
  icon: React.ElementType;
  label: string;
  description: string;
  iconClass: string;
  iconBg: string;
  onClick?: () => void;
}) {
  const inner = (
    <Card className="group flex items-center gap-4 p-4 transition hover:shadow-md cursor-pointer">
      <span className={`shrink-0 rounded-lg p-2.5 ${iconBg}`}>
        <Icon className={`h-4 w-4 ${iconClass}`} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-slate-800">{label}</p>
        <p className="mt-0.5 truncate text-xs text-slate-400">{description}</p>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-300 transition group-hover:text-slate-500" />
    </Card>
  );
  if (onClick) return <button className="text-left w-full" onClick={onClick}>{inner}</button>;
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
  } catch { /* silent fail without backend */ }
}

export function Dashboard() {
  const { data, error, loading, reload } = useAsync(dashboardApi.get, []);
  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const quantumExposure =
    data.metrics.quantum_exposure_percent != null
      ? `${data.metrics.quantum_exposure_percent}%`
      : data.metrics.total_assets > 0
        ? `${Math.round((data.metrics.critical_assets / data.metrics.total_assets) * 100)}%`
        : "—";

  const overallRiskScore =
    data.metrics.average_risk_score != null ? Math.round(data.metrics.average_risk_score) : "—";

  const metrics = [
    { label: "Total Assets Discovered", value: formatNumber(data.metrics.total_assets),   icon: Boxes,       iconBg: "bg-blue-50",   iconClass: "text-blue-600",   sub: `${data.metrics.projects_scanned} projects scanned` },
    { label: "Critical Findings",       value: formatNumber(data.metrics.critical_assets), icon: ShieldAlert, iconBg: "bg-red-50",    iconClass: "text-red-500",    sub: "Require immediate action" },
    { label: "Quantum Exposure",         value: quantumExposure,                           icon: Atom,        iconBg: "bg-violet-50", iconClass: "text-violet-600", sub: "Assets with vulnerable algorithms" },
    { label: "Overall Risk Score",       value: overallRiskScore,                          icon: Activity,    iconBg: "bg-amber-50",  iconClass: "text-amber-600",  sub: `${formatNumber(data.metrics.algorithms_found)} algorithms discovered` },
  ];

  const riskTotal = data.risk_distribution.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Security posture"
        title="Cryptographic risk overview"
        description="A live inventory of cryptographic dependencies, exposure, and migration pressure across your enterprise estate."
        action={
          <Link to="/upload" className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700">
            <ScanLine className="h-4 w-4" /> Start a scan
          </Link>
        }
      />

      {/* Hero stats */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon, iconBg, iconClass, sub }) => (
          <Card key={label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-400">{label}</p>
                <p className="tabular-nums mt-2.5 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
              </div>
              <span className={`rounded-lg p-2.5 ${iconBg}`}><Icon className={`h-5 w-5 ${iconClass}`} /></span>
            </div>
            <p className="mt-4 text-[11px] text-slate-400">{sub}</p>
          </Card>
        ))}
      </section>

      {/* Quick actions */}
      <section>
        <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Quick actions</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <QuickActionButton to="/upload"       icon={ScanLine}        label="Scan Repository"   description="Upload a ZIP or point to a Docker image" iconBg="bg-blue-50"   iconClass="text-blue-600"   />
          <QuickActionButton to="/blast-radius" icon={CircleDotDashed} label="View Blast Radius" description="Simulate crypto asset compromise impact"   iconBg="bg-red-50"    iconClass="text-red-500"    />
          <QuickActionButton icon={FileDown}    label="Generate Report" description="Download full inventory as JSON" iconBg="bg-violet-50" iconClass="text-violet-600" onClick={() => void downloadReport()} />
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-5 xl:grid-cols-[0.85fr_1.4fr]">
        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-slate-800">Risk distribution</p>
          <p className="mt-1 text-xs text-slate-400">Severity across inventoried assets</p>
          {riskTotal ? (
            <div className="relative mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.risk_distribution} dataKey="value" nameKey="name" innerRadius={72} outerRadius={102} paddingAngle={3} stroke="none">
                    {data.risk_distribution.map((item) => <Cell key={item.name} fill={riskColors[item.name] ?? "#94a3b8"} />)}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend iconType="circle" formatter={(value) => <span className="capitalize text-slate-500 text-xs">{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute left-1/2 top-[44%] -translate-x-1/2 -translate-y-1/2 text-center">
                <p className="tabular-nums text-3xl font-semibold text-slate-900">{riskTotal}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">scored</p>
              </div>
            </div>
          ) : <EmptyState title="No scored assets" body="Run a scan to populate the risk model." />}
        </Card>

        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold text-slate-800">Algorithm distribution</p>
          <p className="mt-1 text-xs text-slate-400">Most prevalent cryptographic primitives</p>
          {data.algorithm_distribution.length ? (
            <div className="mt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.algorithm_distribution} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "rgba(59,130,246,.04)" }} contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="value" name="Assets" fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={44} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyState title="No algorithms discovered" body="Algorithm distribution appears after the first completed scan." />}
        </Card>
      </section>

      {/* Recent scans */}
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 md:px-6">
          <div>
            <p className="text-sm font-semibold text-slate-800">Recent scan activity</p>
            <p className="mt-0.5 text-xs text-slate-400">Latest discovery jobs across all sources</p>
          </div>
          <Link to="/upload" className="text-xs font-semibold text-blue-600 hover:text-blue-700">View all →</Link>
        </div>
        {data.recent_scans.length ? (
          <div className="divide-y divide-slate-100">
            {data.recent_scans.slice(0, 5).map((scan) => (
              <div key={scan.id} className="grid gap-3 px-5 py-4 text-sm transition hover:bg-slate-50 md:grid-cols-[1fr_180px_120px_120px] md:items-center md:px-6">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-800">{scan.target}</p>
                  <p className="mt-0.5 text-xs capitalize text-slate-400">{scan.source_type} discovery</p>
                </div>
                <p className="text-xs text-slate-400">{(scan.summary.assets_discovered as number | undefined) ?? 0} assets found</p>
                <StatusBadge status={scan.status} />
                <p className="text-xs text-slate-400 md:text-right">{relativeTime(scan.completed_at ?? scan.created_at)}</p>
              </div>
            ))}
          </div>
        ) : <EmptyState title="No scan activity" body="Upload a repository or provide an infrastructure target to begin." />}
      </Card>
    </div>
  );
}
