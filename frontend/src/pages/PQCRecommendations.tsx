import { ArrowRight, Gauge, KeyRound, Sparkles, type LucideIcon } from "lucide-react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { ShineBorder } from "../components/ShineBorder";
import { useAsync } from "../hooks/useAsync";

export function PQCRecommendations() {
  const { data, error, loading, reload } = useAsync(migrationApi.recommendations, []);
  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const cryptographic = data.filter((item) => !["application", "library"].includes(item.asset_type));
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="PQC decision support"
        title="PQC recommendations"
        description="Compare current primitives with constraint-aware post-quantum and hybrid migration targets."
      />
      {cryptographic.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {cryptographic.map((item, index) => {
            const metrics = item.recommendation.metrics ?? {};
            const card = (
              <Card className="card-hover overflow-hidden">
                <div className="border-b border-zinc-200 bg-zinc-50/60 p-5 md:p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-600">
                        Wave {item.wave} · {item.complexity} complexity
                      </p>
                      <h2 className="mt-1 text-base font-bold text-zinc-950">{item.asset_name}</h2>
                    </div>
                    <Sparkles className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                    <State label="Current" value={item.current_algorithm} icon={KeyRound} />
                    <ArrowRight className="h-4 w-4 text-zinc-400" />
                    <State label="Recommended" value={item.recommended_algorithm} icon={Sparkles} />
                  </div>
                </div>
                <div className="p-5 md:p-6">
                  <p className="text-xs leading-relaxed text-zinc-600">
                    {item.recommendation.reason ?? item.reasons[0]}
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-2.5">
                    {Object.entries(metrics).slice(0, 4).map(([key, value]) => (
                      <div key={key} className="rounded border border-zinc-200 bg-zinc-50 p-2.5">
                        <p className="font-mono text-[9px] font-semibold uppercase tracking-wider text-zinc-500">
                          {key.replaceAll("_", " ")}
                        </p>
                        <p className="mt-0.5 font-mono text-xs font-bold capitalize text-zinc-900">{value}</p>
                      </div>
                    ))}
                  </div>
                  {item.recommendation.hybrid_strategy && (
                    <div className="mt-4 flex items-start gap-2 rounded border border-indigo-200 bg-indigo-50/70 p-3 text-xs leading-relaxed font-medium text-indigo-950">
                      <Gauge className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
                      <span>{item.recommendation.hybrid_strategy}</span>
                    </div>
                  )}
                </div>
              </Card>
            );
            // Top-priority recommendation (Wave 1, first in the API's own
            // priority order) gets the ShineBorder treatment — exactly one
            // card per screen, per issue #67's "signal, not noise" rule.
            return (
              <div key={item.asset_id}>
                {index === 0 ? <ShineBorder>{card}</ShineBorder> : card}
              </div>
            );
          })}
        </div>
      ) : (
        <Card>
          <EmptyState
            title="No PQC recommendations"
            body="Recommendations appear for quantum-vulnerable algorithms and protocols."
          />
        </Card>
      )}
    </div>
  );
}

function State({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  return (
    <div className="rounded border border-zinc-200 bg-white p-3 shadow-xs">
      <Icon className="h-4 w-4 text-indigo-600" strokeWidth={1.75} />
      <p className="mt-2 font-mono text-[9px] font-bold uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-0.5 font-mono text-xs font-bold text-zinc-950">{value}</p>
    </div>
  );
}
