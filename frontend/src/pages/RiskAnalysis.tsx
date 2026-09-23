import { AlertOctagon, CheckCircle2, ChevronRight, Gauge, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { apiErrorMessage, risksApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import type { RiskFinding, Severity } from "../types/api";

const severityOrder: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"];

const severityBarColor: Record<Severity, string> = {
  critical: "var(--risk-critical)",
  high: "var(--risk-high)",
  medium: "var(--risk-medium)",
  low: "var(--risk-low)",
};

export function RiskAnalysis() {
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [data, setData] = useState<Awaited<ReturnType<typeof risksApi.list>> | null>(null);
  const [selected, setSelected] = useState<RiskFinding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(null);
    risksApi.list({ severity: severity === "all" ? undefined : severity, page_size: 100 })
      .then((result) => {
        if (!current) return;
        setData(result);
        setSelected((previous) => result.items.find((item) => item.id === previous?.id) ?? result.items[0] ?? null);
      })
      .catch((caught) => { if (current) setError(caught); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [severity]);

  if (loading) return <LoadingState label="Calculating risk explanations" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} />;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Explainable analysis" title="Cryptographic risk" description="Every score is decomposed into transparent algorithm, dependency, and criticality factors—no black-box prediction." />
      <div className="flex flex-wrap gap-2">
        {severityOrder.map((item) => (
          <button
            key={item}
            onClick={() => setSeverity(item)}
            className={`rounded border px-3 py-1.5 font-mono text-xs font-semibold capitalize transition ${
              severity === item
                ? "border-indigo-600 bg-indigo-50 text-indigo-700 shadow-xs"
                : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:text-zinc-900"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {data.items.length ? (
        <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
          <Card className="max-h-[720px] overflow-y-auto">
            <div className="sticky top-0 z-10 border-b border-zinc-200 bg-white/95 px-5 py-4 backdrop-blur">
              <p className="text-sm font-bold text-zinc-950">Ranked exposure</p>
              <p className="mt-0.5 font-mono text-xs text-zinc-500">{data.total} scored assets</p>
            </div>
            <div className="divide-y divide-zinc-100">
              {data.items.map((risk, index) => (
                <button
                  key={risk.id}
                  onClick={() => setSelected(risk)}
                  className={`interactive flex w-full items-center gap-4 px-5 py-4 text-left ${
                    selected?.id === risk.id
                      ? "bg-indigo-50/70 border-l-2 border-indigo-600 pl-[18px]"
                      : "hover:bg-[var(--bg-hover)]"
                  }`}
                  style={selected?.id !== risk.id ? { background: index % 2 === 1 ? "var(--bg-hover)" : "transparent" } : undefined}
                >
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded border border-zinc-200 bg-zinc-50 font-mono text-xs font-bold text-zinc-950">
                    {Math.round(risk.score)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-zinc-900">{risk.asset_name}</p>
                    <p className="mt-0.5 truncate font-mono text-[11px] text-zinc-500">
                      {risk.project_name} · {risk.asset_type}
                    </p>
                    <div className="mt-1.5 h-1 w-full max-w-[140px] rounded-full" style={{ background: "var(--bg-hover)" }}>
                      <div
                        className="h-1 rounded-full"
                        style={{ width: `${Math.min(100, risk.score)}%`, background: severityBarColor[risk.severity] }}
                      />
                    </div>
                  </div>
                  <SeverityBadge severity={risk.severity} />
                  <ChevronRight className="h-4 w-4 text-zinc-400" />
                </button>
              ))}
            </div>
          </Card>
          {selected && <RiskDetails finding={selected} />}
        </div>
      ) : (
        <Card>
          <EmptyState title="No matching risk findings" body="Choose another severity or complete a discovery scan." />
        </Card>
      )}
    </div>
  );
}

function RiskDetails({ finding }: { finding: RiskFinding }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-zinc-200 bg-zinc-50/60 p-6 md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-center">
          <ScoreGauge score={finding.score} severity={finding.severity} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <SeverityBadge severity={finding.severity} />
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                {finding.asset_type}
              </span>
            </div>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-zinc-950">{finding.asset_name}</h2>
            <p className="mt-1 text-sm text-zinc-500">{finding.project_name}</p>
            <p className="mt-2 break-all font-mono text-xs text-zinc-600 bg-white px-2.5 py-1 rounded border border-zinc-200 inline-block">
              {finding.location}
            </p>
          </div>
        </div>
      </div>
      <div className="space-y-6 p-6 md:p-8">
        <section>
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-zinc-950">Risk explanation</h3>
          </div>
          <div className="mt-3 grid gap-2.5">
            {finding.reasons.map((reason, index) => (
              <div
                key={`${reason}-${index}`}
                className="flex items-start gap-3 rounded border border-zinc-200 bg-zinc-50/50 p-3.5"
              >
                <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <p className="text-sm leading-relaxed text-zinc-800">{reason}</p>
              </div>
            ))}
          </div>
        </section>
        <section>
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-zinc-950">Score composition</h3>
          </div>
          <div className="mt-3 space-y-3.5">
            {finding.factors.map((factor) => (
              <div key={factor.rule_id} className="rounded border border-zinc-200 bg-zinc-50/30 p-3">
                <div className="mb-2 flex items-center justify-between gap-4 text-xs">
                  <div>
                    <span className="font-semibold capitalize text-zinc-900">
                      {factor.category.replaceAll("_", " ")}
                    </span>
                    <span className="ml-2 font-mono text-[10px] text-zinc-500">{factor.rule_id}</span>
                  </div>
                  <span className="font-mono font-bold text-indigo-700">+{factor.points}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded bg-zinc-200">
                  <div
                    className="h-full rounded bg-indigo-600 transition-all"
                    style={{ width: `${Math.min(factor.points, 100)}%` }}
                  />
                </div>
                <p className="mt-2 text-xs leading-relaxed text-zinc-600">{factor.explanation}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded border border-emerald-200 bg-emerald-50/60 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <div>
              <p className="text-sm font-bold text-emerald-950">Analyst next step</p>
              <p className="mt-1 text-xs leading-relaxed text-zinc-700">
                Validate the evidence, identify business owners, and prioritize quantum-vulnerable assets with the highest dependency impact.
              </p>
            </div>
          </div>
        </section>
      </div>
    </Card>
  );
}

function ScoreGauge({ score, severity }: { score: number; severity: Severity }) {
  const color = severityBarColor[severity];
  return (
    <div
      className="relative grid h-32 w-32 shrink-0 place-items-center rounded-full"
      style={{ background: `conic-gradient(${color} ${score * 3.6}deg, var(--border) 0deg)` }}
    >
      <div
        className="grid h-[106px] w-[106px] place-items-center rounded-full text-center shadow-xs border"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        <div>
          <p className="text-3xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>{Math.round(score)}</p>
          <p className="font-mono text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>risk score</p>
        </div>
      </div>
    </div>
  );
}

