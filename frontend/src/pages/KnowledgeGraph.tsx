import { Database, Filter, GitBranch, Info, Network } from "lucide-react";
import { useMemo, useState } from "react";
import ReactFlow, { Background, Controls, Edge, MarkerType, MiniMap, Node, Position } from "reactflow";
import "reactflow/dist/style.css";
import { apiErrorMessage, graphApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { GraphNode } from "../types/api";

const colors: Record<string, string> = {
  project: "#22d3ee",
  application: "#60a5fa",
  library: "#a78bfa",
  algorithm: "#fbbf24",
  certificate: "#34d399",
  protocol: "#fb7185",
  configuration: "#94a3b8",
};

const levelByType: Record<string, number> = {
  project: 0,
  application: 1,
  library: 2,
  protocol: 2,
  configuration: 2,
  algorithm: 3,
  certificate: 3,
};

export function KnowledgeGraph() {
  const { data, error, loading, reload } = useAsync(() => graphApi.get(), []);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [filter, setFilter] = useState("all");

  const graph = useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const visible = data.nodes.filter((node) => filter === "all" || node.type === filter);
    const visibleIds = new Set(visible.map((node) => node.id));
    const buckets = new Map<number, GraphNode[]>();
    for (const item of visible) {
      const level = levelByType[item.type] ?? 2;
      buckets.set(level, [...(buckets.get(level) ?? []), item]);
    }
    const nodes: Node[] = [];
    let yOffset = 40;
    for (const [, items] of Array.from(buckets.entries()).sort(([left], [right]) => left - right)) {
      const columns = Math.min(items.length, 6);
      const width = Math.max(columns - 1, 1) * 210;
      items.forEach((item, index) => {
        nodes.push({
          id: item.id,
          data: { label: item.label, raw: item },
          position: {
            x: (index % columns) * 210 - width / 2 + 600,
            y: yOffset + Math.floor(index / columns) * 145,
          },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          style: {
            width: 178,
            borderRadius: 14,
            border: `1px solid ${colors[item.type] ?? "#64748b"}55`,
            background: "#101f32",
            color: "#e2e8f0",
            padding: "14px 16px",
            fontSize: 12,
            fontWeight: 600,
            boxShadow: `0 10px 30px ${colors[item.type] ?? "#64748b"}12`,
          },
        });
      });
      yOffset += Math.ceil(items.length / columns) * 145 + 70;
    }
    const edges: Edge[] = data.edges
      .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
      .map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.type,
        type: "smoothstep",
        animated: edge.type === "USES",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#475569" },
        style: { stroke: "#475569", strokeWidth: 1.4 },
        labelStyle: { fill: "#64748b", fontSize: 9, fontWeight: 700 },
        labelBgStyle: { fill: "#07101d", fillOpacity: 0.9 },
      }));
    return { nodes, edges };
  }, [data, filter]);

  if (loading) return <LoadingState label="Loading cryptographic topology" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const types = Array.from(new Set(data.nodes.map((node) => node.type))).sort();
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dependency intelligence"
        title="Knowledge graph"
        description="Trace how applications, libraries, algorithms, protocols, and certificates influence one another."
        action={<div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-2 text-[11px] text-slate-400"><Database className="h-3.5 w-3.5 text-brand-300" /> Source: <span className="font-semibold capitalize text-slate-200">{data.source}</span></div>}
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-white/[0.06] px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-500"><Network className="h-4 w-4 text-brand-300" /><span>{data.nodes.length} nodes</span><span className="text-slate-700">·</span><span>{data.edges.length} relationships</span></div>
          <label className="flex items-center gap-2"><Filter className="h-4 w-4 text-slate-600" /><select value={filter} onChange={(event) => { setFilter(event.target.value); setSelected(null); }} className="field w-44 py-2 text-xs"><option value="all">All node types</option>{types.map((type) => <option key={type} value={type} className="capitalize">{type}</option>)}</select></label>
        </div>
        {graph.nodes.length ? (
          <div className="h-[650px] bg-[radial-gradient(circle_at_center,rgba(34,211,238,.035),transparent_60%)]">
            <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView fitViewOptions={{ padding: 0.08, minZoom: 0.5, maxZoom: 0.9 }} minZoom={0.15} maxZoom={1.8} onNodeClick={(_, node) => setSelected((node.data as { raw: GraphNode }).raw)} proOptions={{ hideAttribution: true }}>
              <Background color="#1e334b" gap={28} size={1} />
              <Controls className="graph-controls" />
              <MiniMap nodeColor={(node) => colors[(node.data as { raw?: GraphNode }).raw?.type ?? ""] ?? "#64748b"} maskColor="rgba(7,16,29,.78)" className="graph-minimap" />
            </ReactFlow>
          </div>
        ) : <EmptyState title="No graph nodes available" body="Complete a discovery scan to build the cryptographic topology." />}
      </Card>

      {selected && (
        <Card className="grid gap-5 p-5 md:grid-cols-[auto_1fr_auto] md:items-center md:p-6">
          <span className="rounded-xl p-3" style={{ color: colors[selected.type], background: `${colors[selected.type]}15` }}><GitBranch className="h-5 w-5" /></span>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: colors[selected.type] }}>{selected.type}</p><h2 className="mt-1 font-semibold text-white">{selected.label}</h2><p className="mt-2 font-mono text-xs text-slate-500">{String(selected.properties.location ?? "No location reported")}</p></div>
          <div className="flex items-start gap-2 rounded-xl border border-white/[0.06] bg-black/10 p-3 text-xs leading-5 text-slate-500"><Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-300" /> Risk: <span className="font-semibold capitalize text-slate-300">{String(selected.properties.risk_severity ?? "not scored")}</span></div>
        </Card>
      )}
    </div>
  );
}
