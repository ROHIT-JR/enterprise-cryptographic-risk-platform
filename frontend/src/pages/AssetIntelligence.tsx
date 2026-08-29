import { CheckCircle2, Fingerprint, Network, ShieldAlert } from "lucide-react";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function AssetIntelligence() {
  const { data, error, loading, reload } = useAsync(intelligenceApi.risk, []);
  if (loading) return <LoadingState label="Correlating cryptographic evidence" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Evidence intelligence" title="Asset intelligence" description="Every score remains traceable to discovery channels, business context, and graph-derived impact." />
      {data.items.length ? <div className="grid gap-5 xl:grid-cols-2">{data.items.map((item) => (
        <Card key={item.asset_id} className="p-5 md:p-6">
          <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-300">{item.asset_type}</p><h2 className="mt-2 text-lg font-semibold text-white">{item.asset_name}</h2><p className="mt-1 font-mono text-xs text-slate-500">{item.algorithm ?? "Implementation dependency"}</p></div><div className="text-right"><p className="text-3xl font-semibold text-white">{Math.round(item.final_score)}</p><SeverityBadge severity={item.severity} /></div></div>
          <div className="mt-5 grid grid-cols-3 gap-3"><Metric icon={Fingerprint} label="Confidence" value={`${item.evidence_confidence}%`} /><Metric icon={Network} label="Systems" value={String(item.dependent_systems)} /><Metric icon={ShieldAlert} label="Quantum" value={String(Math.round(item.quantum_score))} /></div>
          <div className="mt-5"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600">Corroborating evidence</p><div className="mt-3 flex flex-wrap gap-2">{item.evidence_sources.map((source) => <span key={source} className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/15 bg-emerald-400/[0.06] px-2.5 py-1.5 text-xs capitalize text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" />{source.replaceAll("_", " ")}</span>)}</div></div>
          <p className="mt-5 line-clamp-2 text-xs leading-5 text-slate-500">{item.explanations[0]}</p>
        </Card>
      ))}</div> : <Card><EmptyState title="No asset intelligence" body="Run a repository, Docker, or TLS scan first." /></Card>}
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Fingerprint; label: string; value: string }) {
  return <div className="rounded-xl bg-black/15 p-3"><Icon className="h-4 w-4 text-brand-300" /><p className="mt-2 text-[10px] uppercase tracking-wider text-slate-600">{label}</p><p className="mt-1 text-sm font-semibold capitalize text-slate-200">{value}</p></div>;
}
