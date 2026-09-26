import { useMemo, useState } from "react";
import {
  Activity,
  Atom,
  Boxes,
  CalendarDays,
  ChevronRight,
  CircleDotDashed,
  FileDown,
  FileText,
  Gauge,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
import {
  ResponsiveContainer, Tooltip,
  XAxis, YAxis, Bar, BarChart, CartesianGrid,
} from "recharts";
import { Link } from "react-router-dom";
import { apiErrorMessage, dashboardApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";
import { ReportGenerator } from "../components/ReportGenerator";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, RadialGauge, StatusBadge } from "../components/ui";
import { NumberTicker } from "../components/NumberTicker";
import { DropdownMenu, DropdownMenuContent, DropdownMenuFieldTrigger, DropdownMenuItem } from "../components/DropdownMenu";
import { useAsync } from "../hooks/useAsync";
import { formatNumber, relativeTime } from "../utils/format";

const PERIOD_OPTIONS = ["This Month", "Last 7 Days", "Last 30 Days", "This Quarter"];

const riskColors: Record<string, string> = {
  critical: "var(--risk-critical)",
  high:     "var(--risk-high)",
  medium:   "var(--risk-medium)",
  low:      "var(--risk-low)",
};

const TOOLTIP_STYLE = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text-primary)",
  fontSize: 11,
  fontFamily: "monospace",
};

function QuickActionButton({
  to,
  icon: Icon,
  label,
  description,
  onClick,
}: {
  to?: string;
  icon: React.ElementType;
  label: string;
  description: string;
  onClick?: () => void;
}) {
  const inner = (
    <Card className="group flex items-center gap-3 p-3.5 transition hover:border-zinc-400 hover:bg-zinc-50/50 cursor-pointer">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-zinc-200 bg-zinc-50 text-zinc-700">
        <Icon className="h-4 w-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-zinc-950 font-sans">{label}</p>
        <p className="mt-0.5 truncate font-mono text-[10px] text-zinc-500">{description}</p>
      </div>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-zinc-400 transition group-hover:text-zinc-800" />
    </Card>
  );
  if (onClick) return <button className="text-left w-full" onClick={onClick}>{inner}</button>;
  return to ? <Link to={to}>{inner}</Link> : inner;
}

export function Dashboard() {
  const { user } = useAuth();
  const canRunScans = user != null && hasPermission(user.role, "run_scans");
  const canExport = user != null && hasPermission(user.role, "export_findings");
  const { data, error, loading, reload } = useAsync(dashboardApi.get, []);
  // State hooks stay above the loading/error early returns below (Rules of Hooks).
  const [reportOpen, setReportOpen] = useState(false);
  const [reportKey, setReportKey] = useState("executive-summary");
  const [period, setPeriod] = useState(PERIOD_OPTIONS[0]);
  const openReports = (key: string) => {
    setReportKey(key);
    setReportOpen(true);
  };

  // Hooks must run unconditionally on every render, so this has to sit above
  // the loading/error early returns below — otherwise the hook is skipped
  // while loading and only starts firing once data arrives, which changes
  // the hook count between renders and crashes React ("Rendered more hooks
  // than during the previous render").
  const computedRiskScore = useMemo(() => {
    if (!data) return { value: 0, sub: "" };
    if (data.metrics.average_risk_score != null) {
      return {
        value: Math.round(data.metrics.average_risk_score),
        sub: `${formatNumber(data.metrics.algorithms_found)} primitives mapped`,
      };
    }
    const total = data.risk_distribution.reduce((sum, item) => sum + item.value, 0);
    if (total === 0) {
      return { value: 0, sub: "No active vulnerabilities" };
    }
    const weights: Record<string, number> = { critical: 95, high: 70, medium: 45, low: 20 };
    const weightedSum = data.risk_distribution.reduce((sum, item) => {
      const w = weights[item.name.toLowerCase()] ?? 30;
      return sum + w * item.value;
    }, 0);
    return {
      value: Math.round(weightedSum / total),
      sub: "Weighted distribution average",
    };
  }, [data]);

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const hasQuantumExposure = data.metrics.quantum_exposure_percent != null;
  const quantumMetric = hasQuantumExposure
    ? {
        label: "Quantum Exposure",
        value: `${data.metrics.quantum_exposure_percent}%`,
        sub: "Shor/Grover vulnerable algorithms",
      }
    : {
        label: "Critical Asset Ratio",
        value:
          data.metrics.total_assets > 0
            ? `${Math.round((data.metrics.critical_assets / data.metrics.total_assets) * 100)}%`
            : "0%",
        sub: "Critical findings / total inventory",
      };

  const criticalRatioPercent = data.metrics.total_assets > 0
    ? Math.round((data.metrics.critical_assets / data.metrics.total_assets) * 100)
    : 0;
  const quantumOrRatioPercent = hasQuantumExposure ? (data.metrics.quantum_exposure_percent ?? 0) : criticalRatioPercent;

  const metrics = [
    { label: "Total Assets Discovered", value: formatNumber(data.metrics.total_assets),   numeric: data.metrics.total_assets,   icon: Boxes,       sub: `${data.metrics.projects_scanned} projects normalized`, barPercent: undefined },
    { label: "Critical Findings",       value: formatNumber(data.metrics.critical_assets), numeric: data.metrics.critical_assets, icon: ShieldAlert, sub: "Immediate migration pressure", alert: true, barPercent: criticalRatioPercent },
    { label: quantumMetric.label,       value: quantumMetric.value,                       numeric: undefined,                    icon: Atom,        sub: quantumMetric.sub, barPercent: quantumOrRatioPercent },
    { label: "Overall Risk Score",       value: computedRiskScore.value,                   numeric: undefined,                    icon: Activity,    sub: computedRiskScore.sub, barPercent: computedRiskScore.value },
  ];

  const riskTotal = data.risk_distribution.reduce((sum, item) => sum + item.value, 0);
  const riskColorFor = (name: string) => riskColors[name] ?? "var(--text-muted)";

  return (
    <div className="page-enter space-y-8">
      <PageHeader
        eyebrow="Posture Intelligence"
        title="Cryptographic Risk Overview"
        description="Real-time telemetry of discovered cryptographic dependencies, quantum exposure horizons, and migration pressure across enterprise estates."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="hidden items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider md:inline-flex"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
            >
              FY 2025-26
            </span>
            <DropdownMenu>
              <DropdownMenuFieldTrigger className="w-36">
                <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" />{period}</span>
              </DropdownMenuFieldTrigger>
              <DropdownMenuContent>
                {PERIOD_OPTIONS.map((option) => (
                  <DropdownMenuItem key={option} selected={option === period} onSelect={() => setPeriod(option)}>
                    {option}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            {canExport && (
              <button type="button" className="btn-secondary" onClick={() => openReports("executive-summary")}>
                <FileText className="h-3.5 w-3.5" /> Generate Report
              </button>
            )}
            {canRunScans && (
              <Link to="/upload" className="btn-primary">
                <ScanLine className="h-3.5 w-3.5" /> Start New Discovery Scan
              </Link>
            )}
          </div>
        }
      />

      {/* Hero stats */}
      <section className="stagger grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, numeric, icon: Icon, sub, alert, barPercent }) => (
          <Card key={label} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{label}</p>
                <p
                  className="tabular-nums font-mono mt-1 text-2xl font-bold tracking-tight"
                  style={{ color: alert ? "var(--risk-critical)" : "var(--text-primary)" }}
                >
                  {numeric !== undefined ? <NumberTicker end={numeric} duration={1.1} /> : value}
                </p>
              </div>
              <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-200 bg-zinc-50 text-zinc-700">
                <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
              </div>
            </div>
            {barPercent !== undefined && (
              <div className="mt-3 h-1 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
                <div
                  className="h-1 rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.max(0, Math.min(100, barPercent))}%`,
                    background: alert ? "var(--risk-critical)" : "var(--accent)",
                  }}
                />
              </div>
            )}
            <p className="mt-3 font-mono text-[10px] text-zinc-500 border-t border-zinc-100 pt-2">{sub}</p>
          </Card>
        ))}
      </section>

      {/* Quick actions */}
      <section>
        <p className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Executive Workflows
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {canRunScans && (
            <QuickActionButton to="/upload" icon={ScanLine} label="Scan Target Repository" description="Ingest source code, container or live TLS endpoint" />
          )}
          <QuickActionButton to="/blast-radius" icon={CircleDotDashed} label="Blast Radius Simulation" description="Simulate systemic compromise propagation on topology" />
          {canExport && (
            <QuickActionButton icon={FileDown} label="Export CBOM Inventory" description="CycloneDX 1.6 CBOM as JSON and PDF" onClick={() => openReports("cbom")} />
          )}
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.3fr]">
        <Card className="p-4">
          <div className="border-b border-zinc-100 pb-2">
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-950">Risk Severity Distribution</p>
            <p className="text-[11px] text-zinc-500">Normalized six-factor risk scoring profile</p>
          </div>
          {riskTotal ? (
            <div className="mt-4 flex flex-col items-center gap-4">
              <RadialGauge
                segments={data.risk_distribution.map((item) => ({ label: item.name, value: item.value, color: riskColorFor(item.name) }))}
                centerValue={riskTotal}
                centerLabel="Total Scored"
                icon={<Gauge className="h-3.5 w-3.5" strokeWidth={1.75} />}
              />
              <div className="w-full space-y-1.5">
                {data.risk_distribution.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: riskColorFor(item.name) }} />
                      <span className="capitalize" style={{ color: "var(--text-secondary)" }}>{item.name}</span>
                    </span>
                    <span className="tabular-nums font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                      {item.value} <span className="font-normal" style={{ color: "var(--text-muted)" }}>({riskTotal ? Math.round((item.value / riskTotal) * 100) : 0}%)</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : <EmptyState title="No scored assets" body="Run a scan to populate the risk model." />}
        </Card>

        <Card className="p-4">
          <div className="border-b border-zinc-100 pb-2">
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-950">Prevalent Algorithms & Primitives</p>
            <p className="text-[11px] text-zinc-500">Asset volume aggregated by cryptographic scheme</p>
          </div>
          {data.algorithm_distribution.length ? (
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.algorithm_distribution} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "var(--text-muted)", fontSize: 10, fontFamily: "monospace" }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
                  <Tooltip cursor={{ fill: "var(--bg-hover)" }} contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="value" name="Assets" fill="var(--accent)" radius={[2, 2, 0, 0]} maxBarSize={36} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyState title="No algorithms discovered" body="Algorithm distribution appears after the first completed scan." />}
        </Card>
      </section>

      {/* Recent scans */}
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-zinc-200 bg-zinc-50 px-4 py-3">
          <div>
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-950">Recent Discovery Pipelines</p>
            <p className="text-[11px] text-zinc-500">Continuous cryptographic ingestion log</p>
          </div>
          {canRunScans && (
            <Link to="/upload" className="font-mono text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Pipeline Console →
            </Link>
          )}
        </div>
        {data.recent_scans.length ? (
          <div className="divide-y divide-zinc-100">
            {data.recent_scans.slice(0, 5).map((scan, index) => (
              <div
                key={scan.id}
                className="interactive grid gap-2 px-4 py-2.5 text-xs hover:bg-[var(--bg-hover)] md:grid-cols-[1fr_160px_110px_110px] md:items-center"
                style={{ background: index % 2 === 1 ? "var(--bg-hover)" : "transparent" }}
              >
                <div className="min-w-0">
                  <p className="truncate font-mono font-semibold text-zinc-900">{scan.target}</p>
                  <p className="font-mono text-[10px] uppercase text-zinc-400">{scan.source_type} scan</p>
                </div>
                <p className="font-mono text-[11px] text-zinc-600">
                  <span className="font-semibold text-zinc-900">{(scan.summary.assets_discovered as number | undefined) ?? 0}</span> assets found
                </p>
                <div>
                  <StatusBadge status={scan.status} />
                </div>
                <p className="font-mono text-[10px] text-zinc-400 md:text-right">{relativeTime(scan.completed_at ?? scan.created_at)}</p>
              </div>
            ))}
          </div>
        ) : <EmptyState title="No scan activity" body="Upload a repository or provide an infrastructure target to begin." />}
      </Card>

      <ReportGenerator open={reportOpen} onClose={() => setReportOpen(false)} initialKey={reportKey} />
    </div>
  );
}
