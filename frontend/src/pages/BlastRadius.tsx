import { CircleDotDashed, Network } from "lucide-react";
import { useMemo } from "react";
import ReactFlow, { Background, Controls, Edge, MarkerType, MiniMap, Node, Position } from "reactflow";
import "reactflow/dist/style.css";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function BlastRadius() {
  const { data, error, loading, reload } = useAsync(() => intelligenceApi.blastRadius(), []);
  const graph = useMemo(() => {
    if (!data?.asset_id) return { nodes: [] as Node[], edges: [] as Edge[] };
    const focus = data.nodes.find((node) => node.id === data.asset_id);
    const dependents = data.nodes.filter((node) => node.id !== data.asset_id);
    const nodes: Node[] = focus ? [{ id: focus.id, data: { label: focus.label }, position: { x: 60, y: 280 }, sourcePosition: Position.Right, style: { width: 210, borderRadius: 16, border: "1px solid rgba(251,113,133,.45)", background: "#231522", color: "#fecdd3", padding: "18px", fontWeight: 700, boxShadow: "0 0 35px rgba(251,113,133,.13)" } }] : [];
    dependents.forEach((node, index) => nodes.push({ id: node.id, data: { label: node.label }, position: { x: 410 + (index % 5) * 205, y: 20 + Math.floor(index / 5) * 105 }, targetPosition: Position.Left, style: { width: 172, borderRadius: 12, border: "1px solid rgba(34,211,238,.18)", background: "#101f32", color: "#cbd5e1", padding: "12px", fontSize: 11 } }));
    const edges: Edge[] = data.edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed, color: "#475569" }, style: { stroke: "#334155", strokeWidth: 1.2 } }));
    return { nodes, edges };
  }, [data]);
  if (loading) return <LoadingState label="Calculating cryptographic blast radius" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Dependency centrality" title="Blast radius visualization" description="See which applications and business services inherit risk from a shared cryptographic dependency." />
      <section className="grid gap-4 md:grid-cols-3"><Card className="p-5"><p className="text-xs text-slate-500">High-impact asset</p><p className="mt-3 font-semibold text-white">{data.asset_name ?? "No analyzed asset"}</p></Card><Card className="p-5"><p className="text-xs text-slate-500">Affected systems</p><p className="mt-3 text-3xl font-semibold text-rose-300">{data.dependent_systems}</p></Card><Card className="p-5"><p className="text-xs text-slate-500">Centrality score</p><p className="mt-3 text-3xl font-semibold text-brand-300">{data.centrality_score.toFixed(2)}</p></Card></section>
      <Card className="overflow-hidden"><div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4 text-xs text-slate-500"><CircleDotDashed className="h-4 w-4 text-brand-300" />Crypto asset → applications → business services</div>{graph.nodes.length ? <div className="h-[680px]"><ReactFlow nodes={graph.nodes} edges={graph.edges} fitView minZoom={0.15} maxZoom={1.6} proOptions={{ hideAttribution: true }}><Background color="#1e334b" gap={28} size={1} /><Controls className="graph-controls" /><MiniMap nodeColor={(node) => node.id === data.asset_id ? "#fb7185" : "#22d3ee"} maskColor="rgba(7,16,29,.8)" className="graph-minimap" /></ReactFlow></div> : <EmptyState title="No blast radius available" body="Complete a scan and assign business context to calculate dependency impact." />}</Card>
      {data.dependent_systems > 0 && <div className="flex items-center gap-3 rounded-xl border border-rose-400/15 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-200"><Network className="h-5 w-5" />Replacing this cryptographic asset affects {data.dependent_systems} systems and requires dependency-aware sequencing.</div>}
    </div>
  );
}
