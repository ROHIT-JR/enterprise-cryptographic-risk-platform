import { AlertTriangle, Atom, Banknote, CheckCircle2, DatabaseZap, ShieldAlert, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
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
import { MoscaSection } from "../components/mosca/MoscaSection";
import { QDayCountdown, type QDayScenario } from "../components/hndl/QDayCountdown";
import { HNDLTimeline } from "../components/hndl/HNDLTimeline";
import { HNDLRiskMatrix, classifyHNDL, type HNDLRow } from "../components/hndl/HNDLRiskMatrix";
import { NumberTicker, NumberTickerLabeled } from "../components/NumberTicker";
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

const SEVERITY_CHART_COLORS: Record<string, string> = {
  critical: "var(--risk-critical)",
  high: "var(--risk-high)",
  medium: "var(--risk-medium)",
  low: "var(--risk-low)",
  secure: "var(--accent)",
  unknown: "var(--text-muted)",
};

const CURRENT_YEAR = new Date().getFullYear();

// Real config default (config/quantum_timeline.json) used as the "Moderate"
// scenario baseline; Optimistic/Pessimistic are +/-5yr heuristic offsets
// around it, not independently-sourced estimates.
const MODERATE_QUANTUM_YEAR = 2035;
const SCENARIO_YEARS: Record<Exclude<QDayScenario, "custom">, number> = {
  optimistic: MODERATE_QUANTUM_YEAR + 5,
  moderate: MODERATE_QUANTUM_YEAR,
  pessimistic: MODERATE_QUANTUM_YEAR - 5,
};

// Illustrative estimate, not measured telemetry — we don't have real
// network traffic volume data, so this scales with how many quantum-
// vulnerable assets were actually discovered. Documented the same way
// estimateDataLifetime() below already documents its own heuristic.
function estimateTbPerYear(vulnerableAssetCount: number): number {
  return Math.round(vulnerableAssetCount * 1.8 * 10) / 10;
}

// Derive data sensitivity label from hndl_risk (no raw sensitivity field
// is returned by the API — hndl_risk is itself derived from it server-side).
function sensitivityLabel(item: IntelligenceItem): string {
  if (item.hndl_risk === "critical") return "top secret";
  if (item.hndl_risk === "high") return "confidential";
  if (item.hndl_risk === "medium") return "sensitive";
  return "internal";
}

// Estimate data lifetime (years) from hndl_score (0-100 -> proxy years).
function estimateDataLifetime(item: IntelligenceItem): number {
  return Math.round((item.hndl_score / 100) * 25) + 3;
}

export function QuantumRiskDashboard() {
  const { data, error, loading, reload } = useAsync(intelligenceApi.risk, []);
  const [scenario, setScenario] = useState<QDayScenario>("moderate");
  const [customYear, setCustomYear] = useState(MODERATE_QUANTUM_YEAR);

  const quantumYear = scenario === "custom" ? customYear : SCENARIO_YEARS[scenario];
  const yearsUntilQuantum = quantumYear - CURRENT_YEAR;

  const hndlRows = useMemo<HNDLRow[]>(() => {
    if (!data) return [];
    return data.items.map((item) => {
      const dataLifetimeYears = estimateDataLifetime(item);
      const quantumSafe = item.quantum_score < 50;
      const status = classifyHNDL({ dataLifetimeYears, quantumSafe, yearsUntilQuantum });
      return {
        assetId: item.asset_id,
        assetName: item.asset_name,
        algorithm: item.algorithm ?? item.asset_type,
        sensitivity: sensitivityLabel(item),
        dataLifetimeYears,
        quantumBreakYear: quantumYear,
        status,
      };
    });
  }, [data, quantumYear, yearsUntilQuantum]);

  if (loading) return <LoadingState label="Calculating quantum risk intelligence" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const metrics = [
    { label: "Vulnerable assets", value: data.metrics.vulnerable_assets, icon: Atom },
    { label: "Critical quantum risks", value: data.metrics.critical_quantum_risks, icon: ShieldAlert },
    { label: "HNDL exposures", value: data.metrics.hndl_exposures, icon: DatabaseZap },
    { label: "Average risk score", value: data.metrics.average_risk_score, icon: ShieldCheck },
  ];

  const atRiskRows = hndlRows.filter((r) => r.status === "at_risk");
  const atRiskCount = atRiskRows.length;
  const topSecretAtRiskCount = atRiskRows.filter((r) => r.sensitivity === "top secret").length;
  const criticalDataOverExposedPercent = hndlRows.length
    ? Math.round((atRiskCount / hndlRows.length) * 100)
    : 0;

  const vulnerableAssetCount = data.metrics.vulnerable_assets;
  const tbPerYear = estimateTbPerYear(vulnerableAssetCount);
  const vulnerableAlgorithms = [...new Set(data.items.filter((i) => i.quantum_score >= 50).map((i) => i.algorithm ?? i.asset_type))];
  const topAtRiskAsset = atRiskRows[0]?.assetName ?? null;
  // How long adversaries have plausibly been harvesting — same illustrative
  // framing as the rest of this page, not a measured start date.
  const yearsHarvestedSoFar = Math.max(1, CURRENT_YEAR - 2020);

  return (
    <div className="page-enter space-y-8">
      <PageHeader
        eyebrow="Phase 2 intelligence"
        title="Quantum risk dashboard"
        description="Prioritize cryptographic exposure using quantum vulnerability, HNDL, blast radius, business impact, migration complexity, and evidence confidence."
      />

      {/* Q-Day Countdown */}
      <QDayCountdown
        scenario={scenario}
        onScenarioChange={setScenario}
        quantumYear={quantumYear}
        customYear={customYear}
        onCustomYearChange={setCustomYear}
      />

      <MoscaSection />

      {/* Metrics row */}
      <section className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon }) => (
          <Card key={label} className="card-hover p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
                <p className="tabular-nums mt-2.5 text-3xl font-semibold" style={{ color: "var(--text-primary)" }}>
                  <NumberTicker end={value} duration={1.1} decimals={Number.isInteger(value) ? 0 : 1} />
                </p>
              </div>
              <span className="rounded-lg p-2.5" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>
                <Icon className="h-5 w-5" />
              </span>
            </div>
          </Card>
        ))}
      </section>

      {/* HNDL Attack Flow */}
      <section className="space-y-3">
        <p className="font-mono text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
          HNDL Attack Flow
        </p>
        <HNDLTimeline
          tbPerYear={tbPerYear}
          algorithmsIntercepted={vulnerableAlgorithms}
          yearsHarvested={yearsHarvestedSoFar}
          topAtRiskAsset={topAtRiskAsset}
        />
      </section>

      {/* Organization HNDL Exposure Summary */}
      <section>
        <p className="mb-3 font-mono text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
          Your HNDL Exposure
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="p-5">
            <NumberTickerLabeled end={atRiskCount} label={`of ${hndlRows.length} assets at HNDL risk`} dotColor="var(--risk-critical)" />
            <div className="mt-3 h-1.5 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
              <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${criticalDataOverExposedPercent}%`, background: "var(--risk-critical)" }} />
            </div>
          </Card>
          <Card className="p-5">
            <NumberTickerLabeled end={topSecretAtRiskCount} label="top-secret assets at risk" dotColor="var(--risk-high)" />
            <div className="mt-3 h-1.5 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
              <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${hndlRows.length ? Math.round((topSecretAtRiskCount / hndlRows.length) * 100) : 0}%`, background: "var(--risk-high)" }} />
            </div>
          </Card>
          <Card className="p-5">
            <NumberTickerLabeled end={criticalDataOverExposedPercent} label="% of scored data at risk" dotColor="var(--accent)" />
            <div className="mt-3 h-1.5 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
              <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${criticalDataOverExposedPercent}%`, background: "var(--accent)" }} />
            </div>
          </Card>
        </div>
        {yearsUntilQuantum > 0 && (
          <p className="mt-3 flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--risk-high)" }} />
            An adversary harvesting your RSA-encrypted traffic today will be able to read it within approximately {yearsUntilQuantum} years.
          </p>
        )}
      </section>

      {/* What's At Stake */}
      <section className="grid gap-4 md:grid-cols-2">
        <Card className="p-5" style={{ borderColor: "var(--risk-critical)" }}>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" style={{ color: "var(--risk-critical)" }} />
            <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>If no action is taken</p>
          </div>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            <li>Customer financial records with long data-retention periods could be exposed once quantum computers arrive.</li>
            <li>Competitor-sensitive business communications intercepted today become decryptable.</li>
            <li>Potential compliance exposure under RBI/NQM cryptographic-modernization guidance.</li>
            <li>
              Average cost of a data breach: <strong style={{ color: "var(--text-primary)" }}>$4.88M</strong> (~₹40.5 crore) — IBM
              Cost of a Data Breach Report 2024. HNDL-driven breaches compound this via retroactive exposure of data harvested years earlier.
            </li>
          </ul>
        </Card>
        <Card className="p-5" style={{ borderColor: "var(--risk-low)" }}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" style={{ color: "var(--risk-low)" }} />
            <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>If migration starts now</p>
          </div>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            <li>Data captured after migration remains protected through the quantum transition.</li>
            <li>Progress toward NQM Phase 1 (cryptographic inventory &amp; assessment) compliance.</li>
            <li>
              Estimated migration effort for currently at-risk assets:{" "}
              <strong style={{ color: "var(--text-primary)" }}>{atRiskCount * 6} engineering hours</strong> — a fraction of the cost of a breach.
            </li>
            <li className="flex items-center gap-1.5">
              <Banknote className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--risk-low)" }} />
              India's National Quantum Mission budget: ₹6,003 crore over 8 years — national-level investment signal for PQC readiness.
            </li>
          </ul>
        </Card>
      </section>

      {/* Charts */}
      <section className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Algorithm vulnerability</p>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Quantum classification across discovered cryptography</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.algorithm_vulnerability_distribution}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12, color: "var(--text-primary)" }} cursor={{ fill: "var(--bg-hover)" }} />
                <Bar dataKey="value" fill="var(--accent)" radius={[6, 6, 0, 0]} maxBarSize={44} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5 md:p-6">
          <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Final risk severity</p>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Normalized ECDAT score from six intelligence factors</p>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.severity_distribution} dataKey="value" nameKey="name" innerRadius={68} outerRadius={105} paddingAngle={3} stroke="none">
                  {data.severity_distribution.map((item) => (
                    <Cell key={item.name} fill={SEVERITY_CHART_COLORS[item.name] ?? "var(--text-muted)"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12, color: "var(--text-primary)" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Per-Asset HNDL Risk Matrix */}
      {hndlRows.length > 0 ? (
        <section>
          <p className="mb-3 font-mono text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
            Per-Asset HNDL Risk Matrix
          </p>
          <HNDLRiskMatrix rows={hndlRows} />
        </section>
      ) : (
        <Card><EmptyState title="No intelligence yet" body="Complete a discovery scan to calculate Phase 2 risk." /></Card>
      )}

      {/* Highest-priority assets table */}
      <Card className="overflow-hidden">
        <div className="border-b px-5 py-4" style={{ borderColor: "var(--border)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Highest-priority assets</p>
        </div>
        {data.items.length ? (
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {data.items.slice(0, 6).map((item, index) => (
              <div
                key={item.asset_id}
                className="interactive grid gap-3 px-5 py-4 hover:bg-[var(--bg-hover)] md:grid-cols-[1fr_140px_140px_120px] md:items-center"
                style={{ background: index % 2 === 1 ? "var(--bg-hover)" : "transparent" }}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{item.asset_name}</p>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{item.algorithm ?? item.asset_type} · {item.dependent_systems} affected systems</p>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>HNDL <span className="font-medium capitalize" style={{ color: "var(--risk-high)" }}>{item.hndl_risk}</span></p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Confidence <span className="font-medium" style={{ color: "var(--accent)" }}>{item.evidence_confidence}%</span></p>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={item.severity} />
                  <span className="tabular-nums font-mono text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{Math.round(item.final_score)}</span>
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
