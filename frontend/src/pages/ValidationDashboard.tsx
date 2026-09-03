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
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4 text-emerald-400">Research & Validation</h1>
        <Card>
          <CardContent className="pt-6 text-center text-slate-400">
            No benchmarks executed yet. Run the benchmark runner to populate research artifacts.
          </CardContent>
        </Card>
      </div>
    );
  }

  const experiments = data.experiments || [];

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-end border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-emerald-400">Research & Validation</h1>
          <p className="text-sm text-slate-400 mt-2">
            Selected ECDAT-X benchmark scenarios were successfully executed on synthetic graphs up to 10,000 nodes.
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
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
                <thead className="bg-slate-800 text-slate-300">
                  <tr>
                    <th className="p-3 rounded-tl">Topology</th>
                    <th className="p-3">Nodes</th>
                    <th className="p-3">Edges</th>
                    <th className="p-3">Total Run (ms)</th>
                    <th className="p-3">Betweenness Centrality</th>
                    <th className="p-3 rounded-tr">Topological Sort (ms)</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.sort((a: any, b: any) => a.nodes - b.nodes).map((exp: any, i: number) => {
                    const bw = exp.stages?.betweenness_centrality;
                    return (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="p-3 capitalize">{exp.topology}</td>
                        <td className="p-3">{exp.graph_nodes}</td>
                        <td className="p-3">{exp.graph_edges}</td>
                        <td className="p-3 font-mono text-emerald-400">{exp.total_duration_ms}</td>
                        <td className="p-3">
                          {bw?.status === "skipped" ? (
                             <div className="flex items-center text-amber-500 gap-1 text-xs" title={bw.reason}>
                               <AlertCircle className="w-4 h-4" /> SKIPPED
                             </div>
                          ) : bw?.status === "measured" ? (
                             <div className="flex items-center text-emerald-500 gap-1 text-xs">
                               <Clock className="w-4 h-4" /> {bw.duration_ms} ms
                             </div>
                          ) : (
                             <span className="text-slate-600">N/A</span>
                          )}
                        </td>
                        <td className="p-3 text-slate-300">
                          {exp.stages?.topological_sort?.duration_ms ?? "N/A"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
             </div>
             <div className="mt-4 p-4 bg-slate-900/50 rounded-lg text-xs text-slate-400 border border-slate-800">
                <p><strong>Environment:</strong> Python {data.environment?.python}, Platform: {data.environment?.platform}, CPU: {data.environment?.cpu}</p>
                <p className="mt-2 text-amber-500/80">
                   * Note: Exact betweenness centrality was intentionally excluded above the configured threshold because of its computational cost.
                </p>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
