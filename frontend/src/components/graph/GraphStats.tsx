import { Atom, GitCompare, Network, Share2, Waypoints } from "lucide-react";
import { NumberTicker } from "../NumberTicker";
import { Card } from "../ui";
import type { GraphStats as GraphStatsData } from "../../types/api";

export function GraphStats({ stats }: { stats: GraphStatsData }) {
  const typeEntries = Object.entries(stats.nodes_by_type).sort(([, a], [, b]) => b - a);

  return (
    <div className="stagger grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <Card className="card-hover p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Total nodes</p>
            <p className="tabular-nums mt-1.5 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              <NumberTicker end={stats.total_nodes} duration={1} />
            </p>
          </div>
          <span className="rounded-lg p-2" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Network className="h-4 w-4" /></span>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-2 gap-y-0.5 text-[10px]" style={{ color: "var(--text-muted)" }}>
          {typeEntries.map(([type, count]) => (
            <span key={type} className="capitalize">{type}: {count}</span>
          ))}
        </div>
      </Card>

      <Card className="card-hover p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Total connections</p>
            <p className="tabular-nums mt-1.5 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              <NumberTicker end={stats.total_edges} duration={1} />
            </p>
          </div>
          <span className="rounded-lg p-2" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Share2 className="h-4 w-4" /></span>
        </div>
      </Card>

      <Card className="card-hover p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Most connected</p>
        {stats.most_connected ? (
          <>
            <p className="mt-1.5 truncate text-sm font-bold" style={{ color: "var(--text-primary)" }}>{stats.most_connected.label}</p>
            <p className="text-xs" style={{ color: "var(--risk-high)" }}>{stats.most_connected_degree} dependencies — highest blast radius</p>
          </>
        ) : (
          <p className="mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>Not enough data</p>
        )}
      </Card>

      <Card className="card-hover p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Top centrality</p>
            {stats.top_centrality ? (
              <>
                <p className="mt-1.5 truncate text-sm font-bold" style={{ color: "var(--text-primary)" }}>{stats.top_centrality.label}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>betweenness {stats.top_centrality_score.toFixed(3)}</p>
              </>
            ) : (
              <p className="mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>Not enough data</p>
            )}
          </div>
          <span className="rounded-lg p-2" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Waypoints className="h-4 w-4" /></span>
        </div>
      </Card>

      <Card className="card-hover p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Communities</p>
            <p className="tabular-nums mt-1.5 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              <NumberTicker end={stats.community_count} duration={1} />
            </p>
          </div>
          <span className="rounded-lg p-2" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><GitCompare className="h-4 w-4" /></span>
        </div>
        <p className="mt-2 text-[10px]" style={{ color: "var(--text-muted)" }}>Detected clusters (Louvain)</p>
      </Card>

      <Card className="card-hover p-4" style={{ borderColor: stats.quantum_vulnerable_count > 0 ? "var(--risk-critical)" : "var(--border)" }}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Quantum-vulnerable</p>
            <p className="tabular-nums mt-1.5 text-2xl font-bold" style={{ color: "var(--risk-critical)" }}>
              <NumberTicker end={stats.quantum_vulnerable_count} duration={1} />
              <span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}> / {stats.quantum_total_count}</span>
            </p>
          </div>
          <span className="rounded-lg p-2" style={{ background: "color-mix(in srgb, var(--risk-critical) 14%, transparent)", color: "var(--risk-critical)" }}><Atom className="h-4 w-4" /></span>
        </div>
        <p className="mt-2 text-[10px]" style={{ color: "var(--text-muted)" }}>algorithms need migration</p>
      </Card>
    </div>
  );
}
