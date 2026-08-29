import { ArrowDown, Route, ShieldCheck } from "lucide-react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { Severity } from "../types/api";

export function MigrationPlanner() {
  const { data, error, loading, reload } = useAsync(migrationApi.roadmap, []);
  if (loading) return <LoadingState label="Building dependency-aware migration waves" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Crypto-agility roadmap" title="Migration planner" description="Migrate trust anchors and shared security components before the applications that depend on them." />
      {data.waves.length ? <div className="space-y-5">{data.waves.map((wave, index) => <div key={wave.wave}><Card className="overflow-hidden"><div className="flex flex-col gap-3 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center"><span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-400/10 font-bold text-brand-300">{wave.wave}</span><div><p className="font-semibold text-white">Wave {wave.wave}: {wave.title}</p><p className="mt-1 text-xs text-slate-500">{wave.reason}</p></div><span className="ml-auto text-xs text-slate-600">{wave.items.length} assets</span></div><div className="divide-y divide-white/[0.05]">{wave.items.slice(0, 16).map((item) => <div key={item.asset_id} className="grid gap-3 px-5 py-4 text-sm md:grid-cols-[1fr_180px_1fr_110px] md:items-center"><div><p className="font-medium text-slate-200">{item.asset_name}</p><p className="mt-1 text-xs capitalize text-slate-600">{item.asset_type}</p></div><p className="font-mono text-xs text-slate-500">{item.current_algorithm}</p><div className="flex items-center gap-2 text-xs text-brand-200"><ShieldCheck className="h-4 w-4" />{item.recommended_algorithm}</div><SeverityBadge severity={(item.complexity === "critical" ? "critical" : item.complexity === "high" ? "high" : item.complexity === "medium" ? "medium" : "low") as Severity} /></div>)}</div></Card>{index < data.waves.length - 1 && <ArrowDown className="mx-auto my-4 h-5 w-5 text-slate-700" />}</div>)}</div> : <Card><EmptyState title="No migration roadmap" body="Quantum-vulnerable assets will appear here after intelligence analysis." /></Card>}
      <div className="flex items-center gap-3 rounded-xl border border-brand-300/15 bg-brand-400/[0.05] px-4 py-3 text-sm text-brand-100"><Route className="h-5 w-5 text-brand-300" />{data.total_assets} assets have been sequenced using dependency-aware ordering.</div>
    </div>
  );
}
