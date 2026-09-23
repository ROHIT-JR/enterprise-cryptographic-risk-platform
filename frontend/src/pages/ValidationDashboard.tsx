import { AlertCircle, Clock } from "lucide-react";
import { useState } from "react";
import { apiErrorMessage, validationApi } from "../api/client";
import { MigrationVerification } from "../components/MigrationVerification";
import { Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { ValidationBaseline } from "../types/api";

type Tab = "migrations" | "scalability";

const TABS: { id: Tab; label: string }[] = [
  { id: "migrations", label: "Migration verification" },
  { id: "scalability", label: "Graph analytics scalability" },
];

function MigrationVerificationPanel() {
  const { data, error, loading, reload } = useAsync(() => validationApi.migrations(), []);
  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  return <MigrationVerification report={data} />;
}

function ScalabilityPanel() {
  const { data, error, loading, reload } = useAsync(() => validationApi.baseline(), []);
  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  if (data.status === "error") return <ErrorState message={data.message} retry={() => void reload()} />;

  const baseline = data.data as Partial<ValidationBaseline>;
  if (data.status === "empty" || !baseline.experiments) {
    return (
      <Card>
        <EmptyState
          title="No benchmarks executed yet"
          body="Run the benchmark runner to populate the research artifacts."
        />
      </Card>
    );
  }

  const experiments = [...baseline.experiments].sort((a, b) => a.nodes - b.nodes);
  return (
    <Card className="card-hover">
      <CardHeader>
        <CardTitle>Graph Analytics Scalability</CardTitle>
        <div className="text-right font-mono text-[11px] text-zinc-500">
          <p>Version: {baseline.benchmark_version}</p>
          {baseline.timestamp && <p>Generated: {new Date(baseline.timestamp).toLocaleString()}</p>}
        </div>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-xs text-zinc-500">
          Selected ECDAT-X benchmark scenarios executed on synthetic graphs up to 10,000 nodes.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-200 bg-zinc-50 text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">
              <tr>
                <th className="p-3">Topology</th>
                <th className="p-3">Nodes</th>
                <th className="p-3">Edges</th>
                <th className="p-3">Total run (ms)</th>
                <th className="p-3">Betweenness centrality</th>
                <th className="p-3">Topological sort (ms)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200">
              {experiments.map((experiment) => {
                const betweenness = experiment.stages.betweenness_centrality;
                return (
                  <tr key={`${experiment.topology}-${experiment.nodes}`} className="interactive hover:bg-zinc-50/80">
                    <td className="p-3 font-semibold capitalize text-zinc-900">{experiment.topology}</td>
                    <td className="p-3 font-mono text-zinc-700">{experiment.graph_nodes}</td>
                    <td className="p-3 font-mono text-zinc-700">{experiment.graph_edges}</td>
                    <td className="p-3 font-mono font-bold text-emerald-700">{experiment.total_duration_ms}</td>
                    <td className="p-3">
                      {betweenness?.status === "skipped" ? (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider"
                          style={{ background: "color-mix(in srgb, var(--risk-medium) 14%, transparent)", color: "var(--risk-medium)" }}
                          title={betweenness.reason}
                        >
                          <AlertCircle className="h-3 w-3" aria-hidden /> Skipped
                        </span>
                      ) : betweenness?.status === "measured" ? (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider"
                          style={{ background: "color-mix(in srgb, var(--risk-low) 14%, transparent)", color: "var(--risk-low)" }}
                        >
                          <Clock className="h-3 w-3" aria-hidden /> {betweenness.duration_ms} ms
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider"
                          style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}
                        >
                          N/A
                        </span>
                      )}
                    </td>
                    <td className="p-3 font-mono text-zinc-700">
                      {experiment.stages.topological_sort?.duration_ms ?? "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 rounded border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-600">
          <p>
            <strong>Environment:</strong> Python {baseline.environment?.python}, Platform: {baseline.environment?.platform}, CPU:{" "}
            {baseline.environment?.cpu}
          </p>
          <p className="mt-2 text-amber-800">
            * Exact betweenness centrality is intentionally skipped above the configured threshold because of its computational
            cost.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function ValidationDashboard() {
  const [tab, setTab] = useState<Tab>("migrations");
  return (
    <div className="page-enter space-y-8">
      <PageHeader
        eyebrow="Research"
        title="Research & Validation"
        description="Migrations are verified, not just planned: each PQC recommendation is checked for compatibility, performance, size, backward compatibility and rollback, with a hybrid path to PQC-only."
      />
      <div role="tablist" aria-label="Validation sections" className="flex gap-1 border-b border-zinc-200">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            type="button"
            id={`validation-tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`validation-panel-${id}`}
            onClick={() => setTab(id)}
            className={`interactive -mb-px border-b-2 px-3 py-2 text-xs font-medium ${
              tab === id ? "border-indigo-600 text-zinc-950" : "border-transparent text-zinc-500 hover:text-zinc-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`validation-panel-${tab}`} aria-labelledby={`validation-tab-${tab}`}>
        {tab === "migrations" ? <MigrationVerificationPanel /> : <ScalabilityPanel />}
      </div>
    </div>
  );
}
