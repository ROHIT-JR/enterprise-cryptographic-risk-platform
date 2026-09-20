import { CheckCircle2, Fingerprint, Network, ShieldAlert } from "lucide-react";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { CryptoAgilityBand } from "../types/api";

const BAND_STYLE: Record<CryptoAgilityBand, { text: string; bg: string; border: string; bar: string }> = {
  "crypto-rigid": { text: "text-red-700", bg: "bg-red-50", border: "border-red-200", bar: "bg-red-500" },
  "crypto-aware": { text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200", bar: "bg-amber-500" },
  "crypto-ready": { text: "text-indigo-700", bg: "bg-indigo-50", border: "border-indigo-200", bar: "bg-indigo-500" },
  "crypto-agile": { text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", bar: "bg-emerald-500" },
};

const BAND_LABEL: Record<CryptoAgilityBand, string> = {
  "crypto-rigid": "Crypto-Rigid",
  "crypto-aware": "Crypto-Aware",
  "crypto-ready": "Crypto-Ready",
  "crypto-agile": "Crypto-Agile",
};

function bandForScore(score: number): CryptoAgilityBand {
  if (score <= 30) return "crypto-rigid";
  if (score <= 60) return "crypto-aware";
  if (score <= 80) return "crypto-ready";
  return "crypto-agile";
}

function CryptoAgilityCard() {
  const { data, error, loading } = useAsync(intelligenceApi.agility, []);
  if (loading) {
    return (
      <Card className="p-5">
        <LoadingState label="Computing crypto-agility score" />
      </Card>
    );
  }
  // Non-blocking: this is a supplementary metric, so a failure here shouldn't
  // take down the rest of the asset intelligence page.
  if (error || !data) return null;

  const style = BAND_STYLE[data.band];
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-zinc-100 p-5 md:flex-row md:items-center md:justify-between md:p-6">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-600">
            Novel metric · Research contribution
          </p>
          <h2 className="mt-1 text-lg font-bold tracking-tight text-zinc-950">Crypto-Agility Score</h2>
          <p className="mt-1 max-w-xl text-xs text-zinc-500">
            How easily this organization can swap cryptographic algorithms without breaking systems.
          </p>
        </div>
        <div className={`flex items-center gap-4 rounded-lg border px-5 py-3 ${style.border} ${style.bg}`}>
          <p className={`text-4xl font-bold tabular-nums ${style.text}`}>{data.score}</p>
          <div>
            <p className={`font-mono text-xs font-bold uppercase tracking-wider ${style.text}`}>
              {BAND_LABEL[data.band]}
            </p>
            <p className="mt-0.5 max-w-[16rem] text-[11px] text-zinc-500">{data.description}</p>
          </div>
        </div>
      </div>
      <div className="grid gap-5 p-5 md:grid-cols-2 md:p-6">
        <div className="space-y-3">
          {data.factors.map((factor) => (
            <div key={factor.factor}>
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-zinc-700">
                  {factor.label} <span className="text-zinc-400">({Math.round(factor.weight * 100)}%)</span>
                </span>
                <span className="font-mono font-semibold text-zinc-800">{factor.score}</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
                <div
                  className={`h-full rounded-full ${BAND_STYLE[bandForScore(factor.score)].bar}`}
                  style={{ width: `${factor.score}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">{factor.explanation}</p>
            </div>
          ))}
        </div>
        <div className="rounded border border-zinc-100 bg-zinc-50 p-4">
          <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-500">
            Recommendations to improve agility
          </p>
          <ul className="mt-2.5 space-y-2 text-xs text-zinc-700">
            {data.recommendations.map((tip) => (
              <li key={tip} className="flex items-start gap-2">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-indigo-500" />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

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
      <CryptoAgilityCard />
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
