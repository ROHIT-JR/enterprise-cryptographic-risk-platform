import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, LoadingState } from "../components/ui";
import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

export function ValidationDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/analytics/validation", {
      headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch validation data");
        return res.json();
      })
      .then(json => {
        if (json.status === "empty") {
          setData(null);
        } else {
          setData(json.data);
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <div className="p-8 text-red-500">Error: {error}</div>;

  if (!data || !data.experiments) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Research & Validation</h1>
        <Card>
          <CardContent className="pt-6 text-center text-zinc-500">
            No benchmarks executed yet. Run the benchmark runner to populate research artifacts.
          </CardContent>
        </Card>
      </div>
    );
  }

  const experiments = data.experiments || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end border-b border-zinc-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Research & Validation</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Selected ECDAT-X benchmark scenarios were successfully executed on synthetic graphs up to 10,000 nodes.
          </p>
        </div>
        <div className="text-right font-mono text-xs text-zinc-500">
          <p>Version: {data.benchmark_version}</p>
          <p>Generated: {new Date(data.timestamp).toLocaleString()}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="col-span-1 md:col-span-2">
          <CardHeader>
            <CardTitle>Graph Analytics Scalability</CardTitle>
          </CardHeader>
          <CardContent>
             <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="border-b border-zinc-200 bg-zinc-50 text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">
                  <tr>
                    <th className="p-3">Topology</th>
                    <th className="p-3">Nodes</th>
                    <th className="p-3">Edges</th>
                    <th className="p-3">Total Run (ms)</th>
                    <th className="p-3">Betweenness Centrality</th>
                    <th className="p-3">Topological Sort (ms)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200">
                  {experiments.sort((a: any, b: any) => a.nodes - b.nodes).map((exp: any, i: number) => {
                    const bw = exp.stages?.betweenness_centrality;
                    return (
                      <tr key={i} className="hover:bg-zinc-50/80 transition">
                        <td className="p-3 font-semibold capitalize text-zinc-900">{exp.topology}</td>
                        <td className="p-3 font-mono text-zinc-700">{exp.graph_nodes}</td>
                        <td className="p-3 font-mono text-zinc-700">{exp.graph_edges}</td>
                        <td className="p-3 font-mono font-bold text-emerald-700">{exp.total_duration_ms}</td>
                        <td className="p-3">
                          {bw?.status === "skipped" ? (
                             <div className="flex items-center text-amber-700 gap-1 font-mono text-xs font-semibold" title={bw.reason}>
                               <AlertCircle className="w-3.5 h-3.5" /> SKIPPED
                             </div>
                          ) : bw?.status === "measured" ? (
                             <div className="flex items-center text-emerald-700 gap-1 font-mono text-xs font-semibold">
                               <Clock className="w-3.5 h-3.5" /> {bw.duration_ms} ms
                             </div>
                          ) : (
                             <span className="font-mono text-zinc-400">N/A</span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-zinc-700">
                          {exp.stages?.topological_sort?.duration_ms ?? "N/A"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
             </div>
             <div className="mt-4 rounded border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-600">
                <p><strong>Environment:</strong> Python {data.environment?.python}, Platform: {data.environment?.platform}, CPU: {data.environment?.cpu}</p>
                <p className="mt-2 text-amber-800">
                   * Note: Exact betweenness centrality was intentionally excluded above the configured threshold because of its computational cost.
                </p>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
