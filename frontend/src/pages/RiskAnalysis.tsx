import { AlertOctagon, CheckCircle2, ChevronRight, Gauge, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { apiErrorMessage, risksApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import type { RiskFinding, Severity } from "../types/api";

const severityOrder: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"];

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
        {severityOrder.map((item) => <button key={item} onClick={() => setSeverity(item)} className={`rounded-full border px-4 py-2 text-xs font-bold capitalize transition ${severity === item ? "border-brand-300/30 bg-brand-400/10 text-brand-200" : "border-white/[0.07] bg-white/[0.025] text-slate-500 hover:text-slate-200"}`}>{item}</button>)}
      </div>

      {data.items.length ? (
        <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
          <Card className="max-h-[720px] overflow-y-auto">
            <div className="sticky top-0 z-10 border-b border-white/[0.06] bg-ink-900/95 px-5 py-4 backdrop-blur"><p className="text-sm font-semibold text-white">Ranked exposure</p><p className="mt-1 text-xs text-slate-500">{data.total} scored assets</p></div>
            <div className="divide-y divide-white/[0.05]">
              {data.items.map((risk) => (
                <button key={risk.id} onClick={() => setSelected(risk)} className={`flex w-full items-center gap-4 px-5 py-4 text-left transition ${selected?.id === risk.id ? "bg-brand-400/[0.065]" : "hover:bg-white/[0.025]"}`}>
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-white/[0.07] bg-black/15 font-mono text-sm font-bold text-white">{Math.round(risk.score)}</div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-200">{risk.asset_name}</p><p className="mt-1 truncate text-[11px] text-slate-600">{risk.project_name} · {risk.asset_type}</p></div>
                  <SeverityBadge severity={risk.severity} /><ChevronRight className="h-4 w-4 text-slate-700" />
                </button>
              ))}
            </div>
          </Card>
          {selected && <RiskDetails finding={selected} />}
        </div>
      ) : <Card><EmptyState title="No matching risk findings" body="Choose another severity or complete a discovery scan." /></Card>}
    </div>
  );
}

function RiskDetails({ finding }: { finding: RiskFinding }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-white/[0.06] bg-gradient-to-br from-white/[0.035] to-transparent p-6 md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-center">
          <ScoreGauge score={finding.score} severity={finding.severity} />
          <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-3"><SeverityBadge severity={finding.severity} /><span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600">{finding.asset_type}</span></div><h2 className="mt-4 text-2xl font-semibold text-white">{finding.asset_name}</h2><p className="mt-2 text-sm text-slate-500">{finding.project_name}</p><p className="mt-3 break-all font-mono text-xs text-slate-600">{finding.location}</p></div>
        </div>
      </div>
      <div className="space-y-8 p-6 md:p-8">
        <section><div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-brand-300" /><h3 className="text-sm font-semibold text-white">Risk explanation</h3></div><div className="mt-4 grid gap-3">{finding.reasons.map((reason, index) => <div key={`${reason}-${index}`} className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-black/10 p-4"><AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" /><p className="text-sm leading-6 text-slate-300">{reason}</p></div>)}</div></section>
        <section><div className="flex items-center gap-2"><Gauge className="h-4 w-4 text-brand-300" /><h3 className="text-sm font-semibold text-white">Score composition</h3></div><div className="mt-4 space-y-4">{finding.factors.map((factor) => <div key={factor.rule_id}><div className="mb-2 flex items-center justify-between gap-4 text-xs"><div><span className="font-semibold capitalize text-slate-300">{factor.category.replaceAll("_", " ")}</span><span className="ml-2 font-mono text-[10px] text-slate-700">{factor.rule_id}</span></div><span className="font-mono font-bold text-white">+{factor.points}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/[0.05]"><div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-brand-300" style={{ width: `${Math.min(factor.points, 100)}%` }} /></div><p className="mt-2 text-xs text-slate-600">{factor.explanation}</p></div>)}</div></section>
        <section className="rounded-xl border border-emerald-400/10 bg-emerald-500/[0.04] p-4"><div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /><div><p className="text-sm font-semibold text-emerald-200">Analyst next step</p><p className="mt-1 text-xs leading-5 text-slate-500">Validate the evidence, identify business owners, and prioritize quantum-vulnerable assets with the highest dependency impact.</p></div></div></section>
      </div>
    </Card>
  );
}

function ScoreGauge({ score, severity }: { score: number; severity: Severity }) {
  const color = severity === "critical" ? "#fb7185" : severity === "high" ? "#fb923c" : severity === "medium" ? "#facc15" : "#34d399";
  return <div className="relative grid h-32 w-32 shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${score * 3.6}deg, rgba(255,255,255,.06) 0deg)` }}><div className="grid h-[106px] w-[106px] place-items-center rounded-full bg-ink-900 text-center"><div><p className="text-3xl font-semibold text-white">{Math.round(score)}</p><p className="text-[9px] font-bold uppercase tracking-[0.16em] text-slate-600">risk score</p></div></div></div>;
}

