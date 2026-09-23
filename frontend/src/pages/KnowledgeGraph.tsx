import { Database, Maximize2, Radar, Search, ShieldAlert, X } from "lucide-react";
import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { apiErrorMessage, graphApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { DropdownMenu, DropdownMenuContent, DropdownMenuFieldTrigger, DropdownMenuItem } from "../components/DropdownMenu";
import { TypedNode, type TypedNodeData } from "../components/graph/TypedNode";
import { GraphStats } from "../components/graph/GraphStats";
import { NodeDetail } from "../components/graph/NodeDetail";
import { useAsync } from "../hooks/useAsync";
import type { GraphNode, Severity } from "../types/api";

const nodeTypes = { typed: TypedNode };

const LEVEL_BY_TYPE: Record<string, number> = {
  project: 0,
  application: 1,
  service: 1,
  library: 2,
  protocol: 2,
  configuration: 2,
  algorithm: 3,
  certificate: 3,
};

const EDGE_STYLE: Record<string, { stroke: string; dash?: string }> = {
  USES: { stroke: "var(--text-muted)" },
  DEPENDS_ON: { stroke: "var(--accent)", dash: "6 3" },
  PROTECTS: { stroke: "var(--q-safe)", dash: "1 3" },
  CONTAINS: { stroke: "var(--border)" },
};

const NODE_TYPE_LABELS: Record<string, string> = {
  project: "Project", application: "Application", library: "Library",
  algorithm: "Algorithm", certificate: "Certificate", protocol: "Protocol",
  configuration: "Configuration", service: "Service",
};

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

function FitViewButton() {
  const { fitView } = useReactFlow();
  return (
    <button
      onClick={() => fitView({ padding: 0.1, duration: 300 })}
      className="interactive absolute right-3 top-3 z-10 flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium shadow-panel"
      style={{ borderColor: "var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)" }}
    >
      <Maximize2 className="h-3.5 w-3.5" /> Fit View
    </button>
  );
}

function GraphCanvas() {
  const { data, error, loading, reload } = useAsync(() => graphApi.get(), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string> | null>(null);
  const [riskFilter, setRiskFilter] = useState<Severity | "all">("all");
  const [algorithmFilter, setAlgorithmFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [riskOverlay, setRiskOverlay] = useState(false);

  const allTypes = useMemo(() => (data ? Array.from(new Set(data.nodes.map((n) => n.type))).sort() : []), [data]);
  const enabledTypes = activeTypes ?? new Set(allTypes);

  const algorithmNames = useMemo(
    () => (data ? Array.from(new Set(data.nodes.filter((n) => n.type === "algorithm").map((n) => n.label))).sort() : []),
    [data],
  );

  const nodeDegree = useMemo(() => {
    const deg = new Map<string, number>();
    if (!data) return deg;
    for (const edge of data.edges) {
      deg.set(edge.source, (deg.get(edge.source) ?? 0) + 1);
      deg.set(edge.target, (deg.get(edge.target) ?? 0) + 1);
    }
    return deg;
  }, [data]);

  const nodesById = useMemo(() => new Map((data?.nodes ?? []).map((n) => [n.id, n])), [data]);

  // 1-hop neighbor set for hover highlighting.
  const hoverNeighborhood = useMemo(() => {
    if (!hoveredId || !data) return null;
    const ids = new Set([hoveredId]);
    for (const edge of data.edges) {
      if (edge.source === hoveredId) ids.add(edge.target);
      if (edge.target === hoveredId) ids.add(edge.source);
    }
    return ids;
  }, [hoveredId, data]);

  const { nodes, edges, visibleCount } = useMemo(() => {
    if (!data) return { nodes: [] as Node<TypedNodeData>[], edges: [] as Edge[], visibleCount: 0 };
    const searchLower = search.trim().toLowerCase();

    const visible = data.nodes.filter((n) => {
      if (!enabledTypes.has(n.type)) return false;
      if (riskFilter !== "all" && n.properties.risk_severity !== riskFilter) return false;
      if (algorithmFilter !== "all" && !(n.type === "algorithm" && n.label === algorithmFilter)) return false;
      return true;
    });
    const visibleIds = new Set(visible.map((n) => n.id));

    const buckets = new Map<number, GraphNode[]>();
    for (const item of visible) {
      const level = LEVEL_BY_TYPE[item.type] ?? 2;
      buckets.set(level, [...(buckets.get(level) ?? []), item]);
    }

    const maxDegree = Math.max(...Array.from(nodeDegree.values()), 1);
    const rfNodes: Node<TypedNodeData>[] = [];
    let yOffset = 40;
    for (const [, items] of Array.from(buckets.entries()).sort(([a], [b]) => a - b)) {
      const columns = Math.min(items.length, 6);
      const width = Math.max(columns - 1, 1) * 200;
      items.forEach((item, index) => {
        const degree = nodeDegree.get(item.id) ?? 0;
        const isSearchMatch = searchLower !== "" && item.label.toLowerCase().includes(searchLower);
        const dimmedBySearch = searchLower !== "" && !isSearchMatch;
        const dimmedByHover = hoverNeighborhood ? !hoverNeighborhood.has(item.id) : false;
        rfNodes.push({
          id: item.id,
          type: "typed",
          data: {
            label: item.label,
            nodeType: item.type,
            severity: (item.properties.risk_severity as Severity) ?? null,
            quantumSafe: item.properties.risk_severity === "low" || item.properties.risk_severity == null,
            degree,
            maxDegree,
            dimmed: dimmedBySearch || dimmedByHover,
            highlighted: isSearchMatch || hoveredId === item.id,
            riskOverlay,
            pulse: riskOverlay && item.type === "algorithm" && (item.properties.risk_severity === "critical" || item.properties.risk_severity === "high"),
          },
          position: { x: (index % columns) * 200 - width / 2 + 620, y: yOffset + Math.floor(index / columns) * 130 },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          draggable: true,
        });
      });
      yOffset += Math.ceil(items.length / columns) * 130 + 60;
    }

    const rfEdges: Edge[] = data.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => {
        const style = EDGE_STYLE[e.type.toUpperCase()] ?? EDGE_STYLE.USES!;
        const dimmedByHover = hoverNeighborhood ? !(hoverNeighborhood.has(e.source) && hoverNeighborhood.has(e.target)) : false;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: hoveredId && !dimmedByHover ? e.type : undefined,
          type: "smoothstep",
          animated: e.type.toUpperCase() === "USES",
          markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
          style: { stroke: style.stroke, strokeWidth: dimmedByHover ? 1 : 1.6, strokeDasharray: style.dash, opacity: dimmedByHover ? 0.15 : 1 },
          labelStyle: { fill: "var(--text-secondary)", fontSize: 9, fontWeight: 700 },
          labelBgStyle: { fill: "var(--bg-card)", fillOpacity: 0.95 },
        };
      });

    return { nodes: rfNodes, edges: rfEdges, visibleCount: visible.length };
  }, [data, enabledTypes, riskFilter, algorithmFilter, search, nodeDegree, hoverNeighborhood, hoveredId, riskOverlay]);

  if (loading) return <LoadingState label="Loading cryptographic topology" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const selectedNode = selectedId ? nodesById.get(selectedId) ?? null : null;

  return (
    <div className="page-enter space-y-6">
      <PageHeader
        eyebrow="Dependency intelligence"
        title="Knowledge graph"
        description="Trace how applications, libraries, algorithms, protocols, and certificates influence one another."
        action={
          <div className="flex items-center gap-2 rounded-lg border px-3 py-1.5 font-mono text-xs" style={{ borderColor: "var(--border)", background: "var(--bg-hover)", color: "var(--text-secondary)" }}>
            <Database className="h-3.5 w-3.5" style={{ color: "var(--accent)" }} />
            Source: <span className="font-bold capitalize" style={{ color: "var(--text-primary)" }}>{data.source}</span>
          </div>
        }
      />

      <GraphStats stats={data.stats} />

      {/* Filter panel */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative flex items-center">
            <Search className="absolute left-3 h-3.5 w-3.5" style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              placeholder="Find RSA-2048…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setSelectedId(null); }}
              className="field w-48 py-2 pl-8 text-xs"
            />
          </label>

          <DropdownMenu>
            <DropdownMenuFieldTrigger className="w-36 capitalize">
              {riskFilter === "all" ? "All risk levels" : riskFilter}
            </DropdownMenuFieldTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem selected={riskFilter === "all"} onSelect={() => setRiskFilter("all")}>All risk levels</DropdownMenuItem>
              {SEVERITIES.map((s) => (
                <DropdownMenuItem key={s} selected={riskFilter === s} onSelect={() => setRiskFilter(s)}>
                  <span className="capitalize">{s}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuFieldTrigger className="w-40">
              {algorithmFilter === "all" ? "All algorithms" : algorithmFilter}
            </DropdownMenuFieldTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem selected={algorithmFilter === "all"} onSelect={() => setAlgorithmFilter("all")}>All algorithms</DropdownMenuItem>
              {algorithmNames.map((name) => (
                <DropdownMenuItem key={name} selected={algorithmFilter === name} onSelect={() => setAlgorithmFilter(name)}>
                  {name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <button
            onClick={() => setRiskOverlay((v) => !v)}
            className="interactive ml-auto flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold"
            style={{
              borderColor: riskOverlay ? "var(--risk-critical)" : "var(--border)",
              background: riskOverlay ? "color-mix(in srgb, var(--risk-critical) 10%, transparent)" : "var(--bg-card)",
              color: riskOverlay ? "var(--risk-critical)" : "var(--text-secondary)",
            }}
          >
            <ShieldAlert className="h-3.5 w-3.5" /> Risk Overlay {riskOverlay ? "On" : "Off"}
          </button>
        </div>

        {/* Type checkboxes */}
        <div className="mt-3 flex flex-wrap gap-2 border-t pt-3" style={{ borderColor: "var(--border)" }}>
          {allTypes.map((type) => {
            const active = enabledTypes.has(type);
            return (
              <button
                key={type}
                onClick={() => {
                  const next = new Set(enabledTypes);
                  if (next.has(type)) next.delete(type); else next.add(type);
                  setActiveTypes(next);
                }}
                className="interactive flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium capitalize"
                style={{
                  borderColor: active ? "var(--accent)" : "var(--border)",
                  background: active ? "var(--accent-soft)" : "var(--bg-card)",
                  color: active ? "var(--accent)" : "var(--text-muted)",
                }}
              >
                {NODE_TYPE_LABELS[type] ?? type}
              </button>
            );
          })}
          {(activeTypes || riskFilter !== "all" || algorithmFilter !== "all" || search) && (
            <button
              onClick={() => { setActiveTypes(null); setRiskFilter("all"); setAlgorithmFilter("all"); setSearch(""); }}
              className="interactive flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px]"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
            >
              <X className="h-3 w-3" /> Clear filters
            </button>
          )}
        </div>

        {riskOverlay && (
          <div className="mt-3 flex flex-wrap gap-3 border-t pt-3 text-[10px]" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            {SEVERITIES.map((s) => (
              <span key={s} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: `var(--risk-${s})` }} /> {s}
              </span>
            ))}
            <span>· pulsing = quantum-vulnerable algorithm</span>
          </div>
        )}
      </Card>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-2 border-b px-5 py-2.5 font-mono text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          <Radar className="h-3.5 w-3.5" style={{ color: "var(--accent)" }} />
          {visibleCount} / {data.nodes.length} nodes · {edges.length} relationships
        </div>
        {nodes.length ? (
          <div className="relative h-[650px]">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.1, minZoom: 0.4, maxZoom: 1 }}
              minZoom={0.15}
              maxZoom={1.8}
              onNodeClick={(_, node) => setSelectedId(node.id)}
              onNodeMouseEnter={(_, node) => setHoveredId(node.id)}
              onNodeMouseLeave={() => setHoveredId(null)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--border)" gap={28} size={1} />
              <Controls className="graph-controls" />
              <MiniMap
                nodeColor={(node) => {
                  const raw = nodesById.get(node.id);
                  return raw?.properties.risk_severity ? `var(--risk-${raw.properties.risk_severity})` : "var(--accent)";
                }}
                maskColor="color-mix(in srgb, var(--bg-app) 65%, transparent)"
                className="graph-minimap"
              />
              <FitViewButton />
            </ReactFlow>
          </div>
        ) : (
          <EmptyState title="No graph nodes available" body={search ? `No nodes match "${search}".` : "Complete a discovery scan to build the cryptographic topology."} />
        )}
      </Card>

      {selectedNode && (
        <div className="page-enter">
          <NodeDetail
            node={selectedNode}
            edges={data.edges}
            nodesById={nodesById}
            onClose={() => setSelectedId(null)}
            onSelectNode={setSelectedId}
          />
        </div>
      )}
    </div>
  );
}

export function KnowledgeGraph() {
  return (
    <ReactFlowProvider>
      <GraphCanvas />
    </ReactFlowProvider>
  );
}
