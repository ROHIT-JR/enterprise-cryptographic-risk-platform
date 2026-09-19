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
      <PageHeader
        eyebrow="Evidence intelligence"
        title="Asset intelligence"
        description="Every score remains traceable to discovery channels, business context, and graph-derived impact."
      />
      {data.items.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {data.items.map((item) => (
            <Card key={item.asset_id} className="p-5 md:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-600">
                    {item.asset_type}
                  </p>
                  <h2 className="mt-2 text-lg font-bold tracking-tight text-zinc-950">{item.asset_name}</h2>
                  <p className="mt-1 font-mono text-xs text-zinc-500">
                    {item.algorithm ?? "Implementation dependency"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold tracking-tight text-zinc-950">{Math.round(item.final_score)}</p>
                  <SeverityBadge severity={item.severity} />
                </div>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3">
                <Metric icon={Fingerprint} label="Confidence" value={`${item.evidence_confidence}%`} />
                <Metric icon={Network} label="Systems" value={String(item.dependent_systems)} />
                <Metric icon={ShieldAlert} label="Quantum" value={String(Math.round(item.quantum_score))} />
              </div>
              <div className="mt-5">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">
                  Corroborating evidence
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {item.evidence_sources.map((source) => (
                    <span
                      key={source}
                      className="inline-flex items-center gap-1.5 rounded border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-mono text-xs font-medium capitalize text-emerald-800"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      {source.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
              <p className="mt-5 line-clamp-2 text-xs leading-relaxed text-zinc-600">{item.explanations[0]}</p>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <EmptyState title="No asset intelligence" body="Run a repository, Docker, or TLS scan first." />
        </Card>
      )}
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Fingerprint; label: string; value: string }) {
  return (
    <div className="rounded border border-zinc-200 bg-zinc-50 p-3">
      <Icon className="h-4 w-4 text-indigo-600" strokeWidth={1.75} />
      <p className="mt-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-0.5 text-sm font-bold capitalize text-zinc-950">{value}</p>
    </div>
  );
}
