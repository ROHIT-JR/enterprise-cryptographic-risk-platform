import { Database, Filter, GitBranch, Info, Network, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { apiErrorMessage, graphApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { GraphNode } from "../types/api";

const colors: Record<string, string> = {
  project:       "#22d3ee",  // cyan
  application:   "#60a5fa",  // blue
  library:       "#a78bfa",  // purple
  algorithm:     "#fbbf24",  // amber
  certificate:   "#34d399",  // emerald
  protocol:      "#fb7185",  // rose
  configuration: "#94a3b8",  // slate
  service:       "#4ade80",  // green
};

const levelByType: Record<string, number> = {
  project: 0,
  application: 1,
  service: 1,
  library: 2,
  protocol: 2,
  configuration: 2,
  algorithm: 3,
  certificate: 3,
};

const NODE_TYPE_LABELS: Record<string, string> = {
  project:       "Project",
  application:   "Application",
  library:       "Library",
  algorithm:     "Algorithm",
  certificate:   "Certificate",
  protocol:      "Protocol",
  configuration: "Configuration",
  service:       "Service",
};

export function KnowledgeGraph() {
  const { data, error, loading, reload } = useAsync(() => graphApi.get(), []);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  // Compute node degree (connection count) for sizing
  const nodeDegree = useMemo(() => {
    if (!data) return new Map<string, number>();
    const deg = new Map<string, number>();
    for (const edge of data.edges) {
      deg.set(edge.source, (deg.get(edge.source) ?? 0) + 1);
      deg.set(edge.target, (deg.get(edge.target) ?? 0) + 1);
    }
    return deg;
  }, [data]);

  const graph = useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };

    const searchLower = search.toLowerCase();
    const visible = data.nodes.filter(
      (node) =>
        (filter === "all" || node.type === filter) &&
        (search === "" || node.label.toLowerCase().includes(searchLower)),
    );
    const visibleIds = new Set(visible.map((node) => node.id));

    const buckets = new Map<number, GraphNode[]>();
    for (const item of visible) {
      const level = levelByType[item.type] ?? 2;
      buckets.set(level, [...(buckets.get(level) ?? []), item]);
    }

    const nodes: Node[] = [];
    let yOffset = 40;
    const maxDegree = Math.max(...Array.from(nodeDegree.values()), 1);

    for (const [, items] of Array.from(buckets.entries()).sort(([left], [right]) => left - right)) {
      const columns = Math.min(items.length, 6);
      const width = Math.max(columns - 1, 1) * 220;

      items.forEach((item, index) => {
        const degree = nodeDegree.get(item.id) ?? 0;
        // Node width scales with degree: min 150, max 210
        const nodeWidth = 150 + Math.round((degree / maxDegree) * 60);
        const isSearchMatch = search !== "" && item.label.toLowerCase().includes(searchLower);

        nodes.push({
          id: item.id,
          data: { label: item.label, raw: item },
          position: {
            x: (index % columns) * 220 - width / 2 + 640,
            y: yOffset + Math.floor(index / columns) * 150,
          },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          style: {
            width: nodeWidth,
            borderRadius: 14,
            border: isSearchMatch
              ? `2px solid ${colors[item.type] ?? "#64748b"}`
              : `1px solid ${colors[item.type] ?? "#64748b"}55`,
            background: isSearchMatch ? `${colors[item.type] ?? "#64748b"}20` : "#101f32",
            color: "#e2e8f0",
            padding: "12px 14px",
            fontSize: degree > (maxDegree * 0.5) ? 13 : 11,
            fontWeight: degree > (maxDegree * 0.5) ? 700 : 600,
            boxShadow: isSearchMatch
              ? `0 0 20px ${colors[item.type] ?? "#64748b"}55`
              : `0 8px 25px ${colors[item.type] ?? "#64748b"}10`,
          },
        });
      });
      yOffset += Math.ceil(items.length / columns) * 150 + 70;
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
  }, [data, filter, search, nodeDegree]);

  if (loading) return <LoadingState label="Loading cryptographic topology" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const types = Array.from(new Set(data.nodes.map((node) => node.type))).sort();

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dependency intelligence"
        title="Knowledge graph"
        description="Trace how applications, libraries, algorithms, protocols, and certificates influence one another."
        action={
          <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-2 text-[11px] text-slate-400">
            <Database className="h-3.5 w-3.5 text-brand-300" />
            Source: <span className="font-semibold capitalize text-slate-200">{data.source}</span>
          </div>
        }
      />

      {/* Node type legend */}
      <div className="flex flex-wrap gap-2">
        {types.map((type) => (
          <button
            key={type}
            onClick={() => setFilter(filter === type ? "all" : type)}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold capitalize transition ${
              filter === type
                ? "border-white/20 bg-white/10 text-white"
                : "border-white/[0.06] bg-white/[0.02] text-slate-400 hover:border-white/10"
            }`}
          >
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: colors[type] ?? "#64748b" }}
            />
            {NODE_TYPE_LABELS[type] ?? type}
          </button>
        ))}
        {filter !== "all" && (
          <button
            onClick={() => setFilter("all")}
            className="flex items-center gap-1 rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-[10px] text-slate-500 hover:text-slate-300"
          >
            <X className="h-3 w-3" /> Clear filter
          </button>
        )}
      </div>

      <Card className="overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-col gap-3 border-b border-white/[0.06] px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Network className="h-4 w-4 text-brand-300" />
            <span>{graph.nodes.length} / {data.nodes.length} nodes</span>
            <span className="text-slate-700">·</span>
            <span>{graph.edges.length} relationships</span>
          </div>
          <div className="flex items-center gap-3">
            {/* Search */}
            <label className="relative flex items-center">
              <Search className="absolute left-3 h-3.5 w-3.5 text-slate-600" />
              <input
                type="text"
                placeholder="Find RSA-2048…"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setSelected(null); }}
                className="field w-48 py-2 pl-8 text-xs"
              />
              {search && (
                <button
                  className="absolute right-2 text-slate-600 hover:text-slate-400"
                  onClick={() => setSearch("")}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </label>
            {/* Filter dropdown (still available for power users) */}
            <label className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-600" />
              <select
                value={filter}
                onChange={(event) => { setFilter(event.target.value); setSelected(null); }}
                className="field w-40 py-2 text-xs"
              >
                <option value="all">All node types</option>
                {types.map((type) => (
                  <option key={type} value={type} className="capitalize">
                    {NODE_TYPE_LABELS[type] ?? type}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {graph.nodes.length ? (
          <div className="h-[650px] bg-[radial-gradient(circle_at_center,rgba(34,211,238,.035),transparent_60%)]">
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              fitView
              fitViewOptions={{ padding: 0.08, minZoom: 0.5, maxZoom: 0.9 }}
              minZoom={0.15}
              maxZoom={1.8}
              onNodeClick={(_, node) => setSelected((node.data as { raw: GraphNode }).raw)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#1e334b" gap={28} size={1} />
              <Controls className="graph-controls" />
              <MiniMap
                nodeColor={(node) =>
                  colors[(node.data as { raw?: GraphNode }).raw?.type ?? ""] ?? "#64748b"
                }
                maskColor="rgba(7,16,29,.78)"
                className="graph-minimap"
              />
            </ReactFlow>
          </div>
        ) : (
          <EmptyState
            title="No graph nodes available"
            body={search ? `No nodes match "${search}". Try a different search term.` : "Complete a discovery scan to build the cryptographic topology."}
          />
        )}
      </Card>

      {/* Node detail panel */}
      {selected && (
        <Card className="animate-fade-in p-5 md:p-6">
          <div className="flex items-start gap-4 md:items-center">
            <span
              className="shrink-0 rounded-xl p-3"
              style={{ color: colors[selected.type], background: `${colors[selected.type]}15` }}
            >
              <GitBranch className="h-5 w-5" />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: colors[selected.type] }}>
                {NODE_TYPE_LABELS[selected.type] ?? selected.type}
              </p>
              <h2 className="mt-1 font-semibold text-white">{selected.label}</h2>
              <p className="mt-1 font-mono text-xs text-slate-500">
                {String(selected.properties.location ?? "No location reported")}
              </p>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Properties grid */}
          <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {/* Risk score */}
            <div className="rounded-xl bg-white/[0.025] px-4 py-3">
              <p className="text-[10px] text-slate-500">Risk severity</p>
              <div className="mt-1.5">
                {(() => {
                  const sev = selected.properties.risk_severity;
                  if (sev && typeof sev === "string") {
                    return <SeverityBadge severity={sev as "critical" | "high" | "medium" | "low"} />;
                  }
                  return <span className="text-xs text-slate-500">Not scored</span>;
                })()}
              </div>
            </div>

            {/* PQC recommendation */}
            {Boolean(selected.properties.recommended_algorithm) && (
              <div className="rounded-xl bg-brand-400/[0.06] border border-brand-400/15 px-4 py-3">
                <p className="text-[10px] text-slate-500">PQC replacement</p>
                <p className="mt-1 text-xs font-semibold text-brand-300">
                  {String(selected.properties.recommended_algorithm)}
                </p>
              </div>
            )}

            {/* Connection count */}
            <div className="rounded-xl bg-white/[0.025] px-4 py-3">
              <p className="text-[10px] text-slate-500">Connections</p>
              <p className="tabular-nums mt-1 text-sm font-semibold text-white">
                {nodeDegree.get(selected.id) ?? 0} relationships
              </p>
            </div>

            {/* All other properties */}
            {Object.entries(selected.properties)
              .filter(([key]) => !["location", "risk_severity", "recommended_algorithm"].includes(key))
              .map(([key, val]) => (
                <div key={key} className="rounded-xl bg-white/[0.025] px-4 py-3">
                  <p className="text-[10px] capitalize text-slate-500">{key.replace(/_/g, " ")}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-slate-200">{String(val ?? "—")}</p>
                </div>
              ))}
          </div>

          {/* View in asset explorer link */}
          <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
            <Info className="h-4 w-4 text-brand-300" />
            <span>Click another node to inspect it, or</span>
            <button onClick={() => setSelected(null)} className="text-brand-300 hover:text-brand-200">
              close panel
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
