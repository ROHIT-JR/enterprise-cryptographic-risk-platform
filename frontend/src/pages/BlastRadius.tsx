import { CircleDotDashed, Network, X, Zap } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
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
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { GraphNode } from "../types/api";

// Animation frame colours
const FRAME_COLORS = {
  0: { bg: "#231522", border: "rgba(251,113,133,.45)", text: "#fecdd3", glow: "0 0 35px rgba(251,113,133,.13)" },   // focus - default
  1: { bg: "#2d0f0f", border: "#ef4444",               text: "#fca5a5", glow: "0 0 40px rgba(239,68,68,.55)" },    // red - compromised
  2: { bg: "#2d1a0a", border: "#f97316",               text: "#fdba74", glow: "0 0 30px rgba(249,115,22,.45)" },   // orange - degree-1
  3: { bg: "#2a2000", border: "#eab308",               text: "#fde047", glow: "0 0 25px rgba(234,179,8,.35)" },    // amber - degree-2
  4: { bg: "#1f2200", border: "#bef264",               text: "#d9f99d", glow: "0 0 18px rgba(190,242,100,.25)" },  // yellow - degree-3
} as const;

const DEP_DEFAULT = { bg: "#101f32", border: "rgba(34,211,238,.18)", text: "#cbd5e1", glow: "none" };

type AnimFrame = 0 | 1 | 2 | 3 | 4;

function buildDegreeMap(assetId: string, edges: { source: string; target: string }[]) {
  const degrees = new Map<string, number>();
  degrees.set(assetId, 0);

  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
    adjacency.get(edge.source)!.push(edge.target);
    adjacency.get(edge.target)!.push(edge.source);
  }

  // BFS from the focus node
  const queue = [assetId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentDeg = degrees.get(current) ?? 0;
    for (const neighbor of adjacency.get(current) ?? []) {
      if (!degrees.has(neighbor)) {
        degrees.set(neighbor, currentDeg + 1);
        queue.push(neighbor);
      }
    }
  }
  return degrees;
}

function getNodeStyle(nodeId: string, assetId: string, degrees: Map<string, number>, frame: AnimFrame) {
  if (nodeId === assetId) {
    const c = FRAME_COLORS[frame];
    return {
      width: 210, borderRadius: 16,
      border: `1px solid ${c.border}`,
      background: c.bg, color: c.text,
      padding: "18px", fontWeight: 700,
      boxShadow: c.glow,
      transition: "all 0.35s ease",
    };
  }
  const deg = degrees.get(nodeId) ?? 99;
  if (frame === 0) return { width: 172, borderRadius: 12, border: DEP_DEFAULT.border, background: DEP_DEFAULT.bg, color: DEP_DEFAULT.text, padding: "12px", fontSize: 11, transition: "all 0.35s ease" };
  const frameMap: Record<number, AnimFrame> = { 1: 2, 2: 3, 3: 4 };
  const frameForDeg = frameMap[deg];
  if (frameForDeg === undefined || frame < frameForDeg) {
    return { width: 172, borderRadius: 12, border: DEP_DEFAULT.border, background: DEP_DEFAULT.bg, color: DEP_DEFAULT.text, padding: "12px", fontSize: 11, transition: "all 0.35s ease" };
  }
  const c = FRAME_COLORS[frameForDeg];
  return { width: 172, borderRadius: 12, border: `1px solid ${c.border}`, background: c.bg, color: c.text, padding: "12px", fontSize: 11, boxShadow: c.glow, transition: "all 0.35s ease" };
}

function getEdgeStyle(edge: { source: string; target: string }, assetId: string, degrees: Map<string, number>, frame: AnimFrame) {
  if (frame === 0) return { stroke: "#334155", strokeWidth: 1.2 };
  const srcDeg = degrees.get(edge.source) ?? 99;
  const tgtDeg = degrees.get(edge.target) ?? 99;
  const minDeg = Math.min(srcDeg, tgtDeg);

  // Activate edges as frames progress
  if (frame >= 1 && minDeg === 0) return { stroke: "#ef4444", strokeWidth: 2, strokeDasharray: "6 3", animation: "edge-flow 0.5s linear infinite" };
  if (frame >= 2 && minDeg === 1) return { stroke: "#f97316", strokeWidth: 1.8, strokeDasharray: "6 3", animation: "edge-flow 0.6s linear infinite" };
  if (frame >= 3 && minDeg === 2) return { stroke: "#eab308", strokeWidth: 1.4, strokeDasharray: "6 3", animation: "edge-flow 0.7s linear infinite" };
  return { stroke: "#334155", strokeWidth: 1.2 };
}

export function BlastRadius() {
  const { data, error, loading, reload } = useAsync(() => intelligenceApi.blastRadius(), []);
  const [frame, setFrame] = useState<AnimFrame>(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showPanel, setShowPanel] = useState(false);

  const { degrees, nodeList } = useMemo(() => {
    if (!data?.asset_id) return { degrees: new Map<string, number>(), nodeList: [] as GraphNode[] };
    return {
      degrees: buildDegreeMap(data.asset_id, data.edges),
      nodeList: data.nodes,
    };
  }, [data]);

  // Impact counts
  const impact = useMemo(() => {
    const d1 = [...degrees.entries()].filter(([, d]) => d === 1).map(([id]) => id);
    const d2 = [...degrees.entries()].filter(([, d]) => d === 2).map(([id]) => id);
    const d3 = [...degrees.entries()].filter(([, d]) => d >= 3).map(([id]) => id);
    return {
      direct: d1.length,
      secondary: d2.length,
      tertiary: d3.length,
      total: d1.length + d2.length + d3.length,
      directNodes: d1.map(id => nodeList.find(n => n.id === id)).filter(Boolean) as GraphNode[],
    };
  }, [degrees, nodeList]);

  const triggerAnimation = useCallback(() => {
    if (isAnimating) return;
    setIsAnimating(true);
    setShowPanel(false);
    setFrame(0);
    const steps: AnimFrame[] = [1, 2, 3, 4];
    steps.forEach((f, i) => {
      setTimeout(() => {
        setFrame(f);
        if (i === steps.length - 1) {
          setIsAnimating(false);
          setShowPanel(true);
        }
      }, (i + 1) * 350);
    });
  }, [isAnimating]);

  const graph = useMemo(() => {
    if (!data?.asset_id) return { nodes: [] as Node[], edges: [] as Edge[] };
    const focus = data.nodes.find((n) => n.id === data.asset_id);
    const dependents = data.nodes.filter((n) => n.id !== data.asset_id);
    const nodes: Node[] = focus
      ? [{ id: focus.id, data: { label: focus.label }, position: { x: 60, y: 280 }, sourcePosition: Position.Right, style: getNodeStyle(focus.id, data.asset_id, degrees, frame) }]
      : [];
    dependents.forEach((node, index) =>
      nodes.push({
        id: node.id,
        data: { label: node.label },
        position: { x: 410 + (index % 5) * 205, y: 20 + Math.floor(index / 5) * 105 },
        targetPosition: Position.Left,
        style: getNodeStyle(node.id, data.asset_id!, degrees, frame),
      }),
    );
    const edges: Edge[] = data.edges.map((edge) => {
      const eStyle = getEdgeStyle(edge, data.asset_id!, degrees, frame);
      return {
        id: edge.id, source: edge.source, target: edge.target,
        type: "smoothstep",
        animated: frame > 0,
        markerEnd: { type: MarkerType.ArrowClosed, color: eStyle.stroke },
        style: eStyle,
      };
    });
    return { nodes, edges };
  }, [data, degrees, frame]);

  if (loading) return <LoadingState label="Calculating cryptographic blast radius" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const frameLabel: Record<AnimFrame, string> = {
    0: "Idle — click to simulate",
    1: "⚡ Asset compromised",
    2: "🔴 Propagating to direct systems…",
    3: "🟠 Reaching secondary dependencies…",
    4: "✅ Full blast radius mapped",
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dependency centrality"
        title="Blast radius visualization"
        description="See which applications and business services inherit risk from a shared cryptographic dependency."
        action={
          <button
            onClick={triggerAnimation}
            disabled={isAnimating}
            className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm font-bold text-rose-300 transition hover:bg-rose-500/20 disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            {isAnimating ? "Simulating…" : `What if ${data.asset_name ?? "this asset"} is compromised?`}
          </button>
        }
      />

      {/* Metrics row */}
      <section className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs text-slate-500">High-impact asset</p>
          <p className="mt-3 font-semibold text-white">{data.asset_name ?? "No analyzed asset"}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-slate-500">Affected systems</p>
          <p className="mt-3 text-3xl font-semibold text-rose-300">{data.dependent_systems}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-slate-500">Centrality score</p>
          <p className="mt-3 text-3xl font-semibold text-brand-300">{data.centrality_score.toFixed(2)}</p>
        </Card>
      </section>

      {/* Animation status bar */}
      {frame > 0 && (
        <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-white/[0.08] bg-ink-850 px-4 py-3 text-sm text-slate-300">
          <span className={`h-2.5 w-2.5 rounded-full ${frame === 4 ? "bg-emerald-400" : "animate-ping bg-rose-400"}`} />
          {frameLabel[frame]}
          <span className="ml-auto text-xs text-slate-600">Frame {frame}/4</span>
        </div>
      )}

      {/* Main layout: graph + optional impact panel */}
      <div className={`flex gap-5 ${showPanel ? "xl:flex-row" : ""}`}>
        <div className="min-w-0 flex-1">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4 text-xs text-slate-500">
              <CircleDotDashed className="h-4 w-4 text-brand-300" />
              Crypto asset → applications → business services
            </div>
            {graph.nodes.length ? (
              <div className="h-[600px]">
                <ReactFlow
                  nodes={graph.nodes}
                  edges={graph.edges}
                  fitView
                  minZoom={0.15}
                  maxZoom={1.6}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background color="#1e334b" gap={28} size={1} />
                  <Controls className="graph-controls" />
                  <MiniMap
                    nodeColor={(node) =>
                      node.id === data.asset_id
                        ? frame > 0 ? "#ef4444" : "#fb7185"
                        : "#22d3ee"
                    }
                    maskColor="rgba(7,16,29,.8)"
                    className="graph-minimap"
                  />
                </ReactFlow>
              </div>
            ) : (
              <EmptyState
                title="No blast radius available"
                body="Complete a scan and assign business context to calculate dependency impact."
              />
            )}
          </Card>
        </div>

        {/* Impact summary panel */}
        {showPanel && (
          <div className="animate-slide-in-right w-full xl:w-80 shrink-0">
            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
                <div className="flex items-center gap-2">
                  <Network className="h-4 w-4 text-rose-400" />
                  <p className="text-sm font-semibold text-white">Blast Radius Impact</p>
                </div>
                <button
                  onClick={() => { setShowPanel(false); setFrame(0); }}
                  className="rounded-lg p-1 text-slate-500 hover:bg-white/5"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="divide-y divide-white/[0.05] px-5">
                {[
                  { label: "Direct (1°) systems", value: impact.direct, color: "text-rose-300" },
                  { label: "Secondary (2°) risk", value: impact.secondary, color: "text-orange-300" },
                  { label: "Tertiary (3°) risk", value: impact.tertiary, color: "text-amber-300" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center justify-between py-3 text-sm">
                    <span className="text-slate-400">{label}</span>
                    <span className={`tabular-nums font-bold ${color}`}>{value}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between py-3 text-sm font-bold">
                  <span className="text-white">Total blast radius</span>
                  <span className="tabular-nums text-rose-300">{impact.total} systems</span>
                </div>
              </div>
              {impact.directNodes.length > 0 && (
                <div className="px-5 pb-5">
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">
                    Directly affected
                  </p>
                  <div className="space-y-2">
                    {impact.directNodes.map((node) => (
                      <div
                        key={node.id}
                        className="flex items-center justify-between rounded-lg bg-white/[0.025] px-3 py-2 text-xs"
                      >
                        <span className="truncate text-slate-300">{node.label}</span>
                        <SeverityBadge
                          severity={
                            ((node.properties.risk_severity as string) ?? "medium") as
                              | "critical"
                              | "high"
                              | "medium"
                              | "low"
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

      {data.dependent_systems > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-400/15 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-200">
          <Network className="h-5 w-5" />
          Replacing this cryptographic asset affects {data.dependent_systems} systems and requires dependency-aware sequencing.
        </div>
      )}
    </div>
  );
}
