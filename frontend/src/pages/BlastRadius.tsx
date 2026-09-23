import { Columns2, Download, Radar, X, Zap } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactFlow, { Background, Controls, MarkerType, MiniMap, Position, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { toPng } from "html-to-image";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { ServiceNode, type ServiceNodeData } from "../components/graph/ServiceNode";
import { ImpactPanel } from "../components/graph/ImpactPanel";
import { AnimFrame, FRAME_DURATIONS_MS, edgeAnimState, nodeAnimState } from "../components/graph/BlastAnimation";
import { useAsync } from "../hooks/useAsync";
import type { BlastRadiusData, GraphNode, Severity } from "../types/api";

const nodeTypes = { service: ServiceNode };

function buildDegreeMap(focusId: string, edges: { source: string; target: string }[]) {
  const degrees = new Map<string, number>();
  degrees.set(focusId, 0);
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
    adjacency.get(edge.source)!.push(edge.target);
    adjacency.get(edge.target)!.push(edge.source);
  }
  const queue = [focusId];
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

function buildGraph(data: BlastRadiusData, frame: AnimFrame): { nodes: Node<ServiceNodeData>[]; edges: Edge[] } {
  if (!data.asset_id) return { nodes: [], edges: [] };
  const degrees = buildDegreeMap(data.asset_id, data.edges);
  const focus = data.nodes.find((n) => n.id === data.asset_id);
  const dependents = data.nodes.filter((n) => n.id !== data.asset_id);

  const nodes: Node<ServiceNodeData>[] = [];
  if (focus) {
    const anim = nodeAnimState({ isFocus: true, degree: 0, realSeverity: (focus.properties.severity as Severity) ?? null, currentFrame: frame });
    nodes.push({
      id: focus.id,
      type: "service",
      position: { x: 40, y: 260 },
      sourcePosition: Position.Right,
      data: {
        name: focus.label,
        nodeType: focus.type,
        algorithm: (focus.properties.algorithm as string) ?? null,
        severity: anim.effectiveSeverity,
        isFocus: true,
        impacted: anim.impacted,
        dimmed: anim.dimmed,
        glow: anim.glow,
      },
    });
  }
  dependents.forEach((node, index) => {
    const degree = degrees.get(node.id) ?? 1;
    const anim = nodeAnimState({ isFocus: false, degree, realSeverity: (node.properties.severity as Severity) ?? null, currentFrame: frame });
    nodes.push({
      id: node.id,
      type: "service",
      position: { x: 380 + (index % 4) * 220, y: 20 + Math.floor(index / 4) * 110 },
      targetPosition: Position.Left,
      data: {
        name: node.label,
        nodeType: node.type,
        algorithm: (node.properties.algorithm as string) ?? null,
        severity: anim.effectiveSeverity,
        impacted: anim.impacted,
        dimmed: anim.dimmed,
        glow: anim.glow,
      },
    });
  });

  const edges: Edge[] = data.edges.map((edge) => {
    const srcDeg = degrees.get(edge.source) ?? 99;
    const tgtDeg = degrees.get(edge.target) ?? 99;
    const anim = edgeAnimState({ minDegree: Math.min(srcDeg, tgtDeg), currentFrame: frame });
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      animated: anim.animated,
      markerEnd: { type: MarkerType.ArrowClosed, color: anim.stroke },
      style: { stroke: anim.stroke, strokeWidth: anim.strokeWidth, strokeDasharray: anim.dashed ? "6 3" : undefined },
    };
  });

  return { nodes, edges };
}

function MiniGraph({ data, title, onClose }: { data: BlastRadiusData; title: string; onClose?: () => void }) {
  const { nodes, edges } = useMemo(() => buildGraph(data, 4), [data]);
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b px-4 py-2.5 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        <span>{title}</span>
        {onClose && (
          <button onClick={onClose} className="interactive rounded p-1 hover:bg-[var(--bg-hover)]">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="h-[420px]">
        {nodes.length ? (
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.15} maxZoom={1.4} proOptions={{ hideAttribution: true }} nodesDraggable={false}>
            <Background color="var(--border)" gap={28} size={1} />
          </ReactFlow>
        ) : (
          <EmptyState title="No data" body="This asset has no mapped dependents." />
        )}
      </div>
    </Card>
  );
}

export function BlastRadius() {
  const navigate = useNavigate();
  const [selectedAssetId, setSelectedAssetId] = useState<string | undefined>(undefined);
  const { data, error, loading, reload } = useAsync(() => intelligenceApi.blastRadius(selectedAssetId), [selectedAssetId]);

  const [compareAssetId, setCompareAssetId] = useState<string | undefined>(undefined);
  const [compareMode, setCompareMode] = useState(false);
  const { data: compareData } = useAsync(
    () => (compareAssetId ? intelligenceApi.blastRadius(compareAssetId) : Promise.resolve(null)),
    [compareAssetId],
  );

  const [frame, setFrame] = useState<AnimFrame>(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const timeoutsRef = useRef<number[]>([]);
  const graphWrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => timeoutsRef.current.forEach((t) => window.clearTimeout(t)), []);

  const triggerAnimation = useCallback(() => {
    if (isAnimating) return;
    timeoutsRef.current.forEach((t) => window.clearTimeout(t));
    timeoutsRef.current = [];
    setIsAnimating(true);
    setShowPanel(false);
    setFrame(0);
    const steps: AnimFrame[] = [1, 2, 3, 4];
    let elapsed = 0;
    steps.forEach((f, i) => {
      elapsed += FRAME_DURATIONS_MS[i] ?? 300;
      const tid = window.setTimeout(() => {
        setFrame(f);
        if (i === steps.length - 1) {
          setIsAnimating(false);
          setShowPanel(true);
        }
      }, elapsed);
      timeoutsRef.current.push(tid);
    });
  }, [isAnimating]);

  const graph = useMemo(() => (data ? buildGraph(data, frame) : { nodes: [], edges: [] }), [data, frame]);

  const directNodes = useMemo<GraphNode[]>(() => {
    if (!data?.asset_id) return [];
    const degrees = buildDegreeMap(data.asset_id, data.edges);
    return data.nodes.filter((n) => degrees.get(n.id) === 1);
  }, [data]);

  const handleNodeClick = useCallback(
    (_: unknown, node: Node<ServiceNodeData>) => {
      if (node.data.nodeType !== "algorithm" && !node.data.isFocus) return;
      if (compareMode && node.id !== selectedAssetId) {
        setCompareAssetId(node.id);
        return;
      }
      if (node.id !== selectedAssetId) {
        setSelectedAssetId(node.id);
      } else {
        triggerAnimation();
      }
    },
    [compareMode, selectedAssetId, triggerAnimation],
  );

  // Auto-run the propagation animation once a fresh asset's data lands.
  useEffect(() => {
    if (data?.asset_id) triggerAnimation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.asset_id]);

  const exportPng = useCallback(() => {
    if (!graphWrapperRef.current) return;
    void toPng(graphWrapperRef.current, {
      backgroundColor: "var(--bg-app)",
      pixelRatio: 2,
    }).then((dataUrl) => {
      const link = document.createElement("a");
      link.download = `blast-radius-${data?.asset_name ?? "export"}.png`;
      link.href = dataUrl;
      link.click();
    });
  }, [data?.asset_name]);

  if (loading && !data) return <LoadingState label="Calculating cryptographic blast radius" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const impact = data.impact_summary;
  const criticalShare = impact.total_affected > 0 ? Math.round((impact.critical_systems / impact.total_affected) * 100) : 0;

  const frameLabel: Record<AnimFrame, string> = {
    0: "Idle — click an algorithm node to simulate compromise",
    1: "Asset compromised",
    2: "Propagating to direct systems…",
    3: "Reaching secondary dependencies…",
    4: "Full blast radius mapped",
  };

  return (
    <div className="page-enter space-y-6">
      <PageHeader
        eyebrow="Dependency centrality"
        title="Blast radius visualization"
        description="See which applications and business services inherit risk from a shared cryptographic dependency."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setCompareMode((v) => !v)}
              className={`interactive inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-semibold ${compareMode ? "" : ""}`}
              style={{
                borderColor: compareMode ? "var(--accent)" : "var(--border)",
                background: compareMode ? "var(--accent-soft)" : "var(--bg-card)",
                color: compareMode ? "var(--accent)" : "var(--text-secondary)",
              }}
            >
              <Columns2 className="h-4 w-4" /> What-If Compare
            </button>
            <button onClick={exportPng} className="interactive btn-secondary">
              <Download className="h-3.5 w-3.5" /> Export PNG
            </button>
            <button
              onClick={triggerAnimation}
              disabled={isAnimating}
              className="interactive inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-bold disabled:opacity-50"
              style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 10%, transparent)", color: "var(--risk-critical)" }}
            >
              <Zap className="h-4 w-4" />
              {isAnimating ? "Simulating…" : `What if ${data.asset_name ?? "this asset"} is compromised?`}
            </button>
          </div>
        }
      />

      {/* Risk storytelling — real numbers only, no fabricated timeline */}
      {data.asset_id && (
        <div
          className="rounded-xl border px-4 py-3.5 text-sm leading-relaxed"
          style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 6%, transparent)", color: "var(--text-secondary)" }}
        >
          If <strong style={{ color: "var(--text-primary)" }}>{data.asset_name}</strong> is compromised,{" "}
          <strong style={{ color: "var(--risk-critical)" }}>{impact.total_affected} system{impact.total_affected === 1 ? "" : "s"}</strong>{" "}
          {impact.total_affected === 1 ? "is" : "are"} affected
          {impact.total_affected > 0 && (
            <> — <strong style={{ color: "var(--text-primary)" }}>{criticalShare}%</strong> of those are critical or high-criticality systems.</>
          )}{" "}
          Estimated remediation effort is <strong style={{ color: "var(--text-primary)" }}>{impact.estimated_effort_hours} engineering hours</strong> once migration begins.
        </div>
      )}

      {/* Metrics row */}
      <section className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>High-impact asset</p>
          <p className="mt-2 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{data.asset_name ?? "No analyzed asset"}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>Affected systems</p>
          <p className="mt-2 text-3xl font-semibold" style={{ color: "var(--risk-critical)" }}>{data.dependent_systems}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>Centrality score</p>
          <p className="mt-2 text-3xl font-semibold" style={{ color: "var(--accent)" }}>{data.centrality_score.toFixed(2)}</p>
        </Card>
      </section>

      {frame > 0 && (
        <div
          className="page-enter flex items-center gap-3 rounded-xl border px-4 py-3 text-sm"
          style={{ borderColor: "var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)" }}
        >
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: frame === 4 ? "var(--risk-low)" : "var(--risk-critical)", animation: frame === 4 ? "none" : "pulse-glow-red 1.2s ease-in-out infinite" }}
          />
          {frameLabel[frame]}
          <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>Frame {frame}/4</span>
        </div>
      )}

      {/* Main layout: graph + optional impact panel */}
      <div className={`flex gap-5 ${showPanel ? "xl:flex-row" : ""}`}>
        <div className="min-w-0 flex-1 space-y-5">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 border-b px-5 py-3.5 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              <Radar className="h-4 w-4" style={{ color: "var(--accent)" }} />
              Crypto asset → applications → business services
            </div>
            {graph.nodes.length ? (
              <div className="h-[600px]" ref={graphWrapperRef}>
                <ReactFlow
                  nodes={graph.nodes}
                  edges={graph.edges}
                  nodeTypes={nodeTypes}
                  onNodeClick={handleNodeClick}
                  fitView
                  minZoom={0.15}
                  maxZoom={1.6}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background color="var(--border)" gap={28} size={1} />
                  <Controls className="graph-controls" />
                  <MiniMap
                    nodeColor={(node) => (node.id === data.asset_id ? (frame > 0 ? "var(--risk-critical)" : "var(--accent-soft)") : "var(--accent)")}
                    maskColor="color-mix(in srgb, var(--bg-app) 55%, transparent)"
                    className="graph-minimap"
                  />
                </ReactFlow>
              </div>
            ) : (
              <EmptyState title="No blast radius available" body="Complete a scan and assign business context to calculate dependency impact." />
            )}
          </Card>

          {compareMode && compareData?.asset_id && (
            <MiniGraph data={compareData} title={`Compare: ${compareData.asset_name}`} onClose={() => setCompareAssetId(undefined)} />
          )}
          {compareMode && !compareAssetId && (
            <div className="rounded-xl border border-dashed px-4 py-6 text-center text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              What-If Compare is on — click another algorithm node above to see its blast radius side by side.
            </div>
          )}
        </div>

        {/* Impact summary panel */}
        {showPanel && (
          <div className="page-enter w-full xl:w-96 shrink-0">
            <ImpactPanel
              assetName={data.asset_name ?? "Unknown asset"}
              impactSummary={impact}
              directNodes={directNodes}
              onClose={() => { setShowPanel(false); setFrame(0); }}
              onViewMigrationPlan={() => navigate("/migration")}
              onGenerateReport={() => navigate("/audit")}
            />
            {compareMode && compareData?.impact_summary && compareData.asset_id && (
              <div className="mt-4">
                <ImpactPanel
                  assetName={compareData.asset_name ?? "Unknown asset"}
                  impactSummary={compareData.impact_summary}
                  directNodes={[]}
                  onClose={() => setCompareAssetId(undefined)}
                  onViewMigrationPlan={() => navigate("/migration")}
                  onGenerateReport={() => navigate("/audit")}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
