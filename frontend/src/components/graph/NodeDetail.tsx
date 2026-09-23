import { ArrowRight, CircleDotDashed, Link2, Sparkles, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card, SeverityBadge } from "../ui";
import type { GraphEdge, GraphNode, Severity } from "../../types/api";

const NODE_TYPE_LABELS: Record<string, string> = {
  project: "Project",
  application: "Application",
  library: "Library",
  algorithm: "Algorithm",
  certificate: "Certificate",
  protocol: "Protocol",
  configuration: "Configuration",
  service: "Service",
};

/** Nodes that reach `nodeId` by following edges (BFS) — a real, computed blast-radius count. */
function reachableCount(nodeId: string, edges: GraphEdge[]): number {
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
    adjacency.get(edge.source)!.push(edge.target);
    adjacency.get(edge.target)!.push(edge.source);
  }
  const visited = new Set([nodeId]);
  const queue = [nodeId];
  while (queue.length) {
    const current = queue.shift()!;
    for (const neighbor of adjacency.get(current) ?? []) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push(neighbor);
      }
    }
  }
  return visited.size - 1;
}

export function NodeDetail({
  node,
  edges,
  nodesById,
  onClose,
  onSelectNode,
}: {
  node: GraphNode;
  edges: GraphEdge[];
  nodesById: Map<string, GraphNode>;
  onClose: () => void;
  onSelectNode: (id: string) => void;
}) {
  const navigate = useNavigate();
  const usedBy = edges
    .filter((e) => e.target === node.id && (e.type === "USES" || e.type === "DEPENDS_ON"))
    .map((e) => nodesById.get(e.source))
    .filter((n): n is GraphNode => Boolean(n));
  const blastRadius = reachableCount(node.id, edges);
  const severity = node.properties.risk_severity as Severity | undefined;
  const recommendedAlgorithm = node.properties.recommended_algorithm as string | undefined;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start gap-4 border-b p-5" style={{ borderColor: "var(--border)" }}>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: "var(--accent)" }}>
            {NODE_TYPE_LABELS[node.type] ?? node.type}
          </p>
          <h2 className="mt-1 truncate font-semibold" style={{ color: "var(--text-primary)" }}>{node.label}</h2>
          {Boolean(node.properties.location) && (
            <p className="mt-1 truncate font-mono text-xs" style={{ color: "var(--text-muted)" }}>{String(node.properties.location)}</p>
          )}
        </div>
        <button onClick={onClose} className="interactive shrink-0 rounded-lg p-1.5 hover:bg-[var(--bg-hover)]" style={{ color: "var(--text-muted)" }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-2.5 p-5 sm:grid-cols-2">
        <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}>
          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Risk severity</p>
          <div className="mt-1.5">
            {severity ? <SeverityBadge severity={severity} /> : <span className="text-xs" style={{ color: "var(--text-muted)" }}>Not scored</span>}
          </div>
        </div>
        {typeof node.properties.risk_score === "number" && (
          <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}>
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Risk score</p>
            <p className="tabular-nums mt-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {Math.round(node.properties.risk_score as number)}/100
            </p>
          </div>
        )}
        <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}>
          <p className="flex items-center gap-1 text-[10px]" style={{ color: "var(--text-muted)" }}><CircleDotDashed className="h-3 w-3" /> Blast radius</p>
          <p className="tabular-nums mt-1 text-sm font-semibold" style={{ color: blastRadius > 0 ? "var(--risk-high)" : "var(--text-primary)" }}>
            {blastRadius} reachable nodes
          </p>
        </div>
        {recommendedAlgorithm && (
          <div className="rounded-xl border p-3" style={{ borderColor: "var(--accent)", background: "var(--accent-soft)" }}>
            <p className="flex items-center gap-1 text-[10px]" style={{ color: "var(--accent)" }}><Sparkles className="h-3 w-3" /> PQC recommendation</p>
            <p className="mt-1 text-xs font-semibold" style={{ color: "var(--accent)" }}>{recommendedAlgorithm}</p>
          </div>
        )}
      </div>

      {usedBy.length > 0 && (
        <div className="border-t px-5 py-4" style={{ borderColor: "var(--border)" }}>
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            <Link2 className="h-3 w-3" /> Used by
          </p>
          <div className="flex flex-wrap gap-1.5">
            {usedBy.slice(0, 8).map((n) => (
              <button
                key={n.id}
                onClick={() => onSelectNode(n.id)}
                className="interactive rounded-full border px-2.5 py-1 text-[11px]"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
              >
                {n.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="border-t p-5" style={{ borderColor: "var(--border)" }}>
        <button onClick={() => navigate("/risks")} className="interactive btn-primary w-full justify-between">
          View Full Analysis <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </Card>
  );
}
