import { ArrowRight, Gauge, KeyRound, Sparkles, type LucideIcon } from "lucide-react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function PQCRecommendations() {
  const { data, error, loading, reload } = useAsync(migrationApi.recommendations, []);
  if (loading) return <LoadingState label="Selecting post-quantum alternatives" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const cryptographic = data.filter((item) => !["application", "library"].includes(item.asset_type));
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="PQC decision support" title="PQC recommendations" description="Compare current primitives with constraint-aware post-quantum and hybrid migration targets." />
      {cryptographic.length ? <div className="grid gap-5 xl:grid-cols-2">{cryptographic.map((item) => {
        const metrics = item.recommendation.metrics ?? {};
        return <Card key={item.asset_id} className="overflow-hidden"><div className="border-b border-white/[0.06] p-5 md:p-6"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-300">Wave {item.wave} · {item.complexity} complexity</p><h2 className="mt-2 font-semibold text-white">{item.asset_name}</h2></div><Sparkles className="h-5 w-5 text-brand-300" /></div><div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-3"><State label="Current" value={item.current_algorithm} icon={KeyRound} /><ArrowRight className="h-5 w-5 text-slate-700" /><State label="Recommended" value={item.recommended_algorithm} icon={Sparkles} /></div></div><div className="p-5 md:p-6"><p className="text-xs leading-5 text-slate-400">{item.recommendation.reason ?? item.reasons[0]}</p><div className="mt-5 grid grid-cols-2 gap-3">{Object.entries(metrics).slice(0, 4).map(([key, value]) => <div key={key} className="rounded-lg bg-black/15 p-3"><p className="text-[9px] uppercase tracking-wider text-slate-600">{key.replaceAll("_", " ")}</p><p className="mt-1 text-xs capitalize text-slate-300">{value}</p></div>)}</div>{item.recommendation.hybrid_strategy && <div className="mt-4 flex gap-2 rounded-lg border border-brand-300/10 bg-brand-400/[0.04] p-3 text-xs text-brand-100"><Gauge className="mt-0.5 h-4 w-4 shrink-0 text-brand-300" />{item.recommendation.hybrid_strategy}</div>}</div></Card>;
      })}</div> : <Card><EmptyState title="No PQC recommendations" body="Recommendations appear for quantum-vulnerable algorithms and protocols." /></Card>}
    </div>
  );
}

function State({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) { return <div className="rounded-xl bg-black/15 p-4"><Icon className="h-4 w-4 text-brand-300" /><p className="mt-3 text-[9px] font-bold uppercase tracking-wider text-slate-600">{label}</p><p className="mt-1 text-sm font-semibold text-slate-200">{value}</p></div>; }
