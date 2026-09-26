import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Building2, KeyRound, Lock, Package, Server, ShieldQuestion } from "lucide-react";
import type { Severity } from "../../types/api";

export interface ServiceNodeData {
  name: string;
  /** Backend asset_type: project | application | algorithm | library | certificate | protocol | configuration */
  nodeType: string;
  algorithm?: string | null;
  severity?: Severity | null;
  /** Only meaningful for algorithm nodes. */
  quantumSafe?: boolean;
  isFocus?: boolean;
  /** Set by the blast-radius animation sequence — see BlastAnimation.ts. */
  impacted?: boolean;
  dimmed?: boolean;
  glow?: boolean;
}

const TYPE_ICON: Record<string, typeof Server> = {
  project: Building2,
  organization: Building2,
  application: Server,
  service: Server,
  algorithm: KeyRound,
  library: Package,
  certificate: Lock,
  protocol: Lock,
  configuration: ShieldQuestion,
};

function riskVar(severity: Severity | null | undefined): string {
  if (!severity) return "var(--border)";
  return `var(--risk-${severity})`;
}

function typeAccent(nodeType: string, quantumSafe?: boolean): string {
  switch (nodeType) {
    case "project":
    case "organization":
      return "var(--accent)";
    case "algorithm":
      return quantumSafe ? "var(--risk-low)" : "var(--risk-critical)";
    case "library":
      return "var(--tint-library)";
    case "certificate":
    case "protocol":
      return "var(--tint-protocol)";
    default:
      return "var(--text-muted)";
  }
}

/**
 * Card-style ReactFlow node — name, algorithm (when known), risk badge,
 * type icon. Colored by node type per issue #69; risk-impacted state
 * (pulsing/glowing during the blast-radius animation) is driven by the
 * `impacted`/`dimmed`/`glow` data flags, not by a separate style prop, so
 * the same node component works for both the idle graph and every
 * animation frame.
 */
export const ServiceNode = memo(function ServiceNode({ data }: NodeProps<ServiceNodeData>) {
  const Icon = TYPE_ICON[data.nodeType] ?? Server;
  const accent = typeAccent(data.nodeType, data.quantumSafe);
  const borderColor = data.impacted ? riskVar(data.severity) : data.isFocus ? accent : "var(--border)";

  return (
    <div
      className="card-hover interactive rounded-lg border px-3 py-2.5"
      style={{
        background: data.isFocus ? "var(--accent-soft)" : "var(--bg-card)",
        borderColor,
        borderWidth: data.isFocus || data.impacted ? 1.5 : 1,
        opacity: data.dimmed ? 0.3 : 1,
        minWidth: 172,
        boxShadow: data.glow ? `0 0 14px ${riskVar(data.severity)}` : "none",
        transition: "opacity 300ms ease, border-color 300ms ease, box-shadow 300ms ease",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "var(--border-strong)" }} />
      <Handle type="source" position={Position.Right} style={{ background: "var(--border-strong)" }} />
      <div className="flex items-center gap-2">
        <span
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md"
          style={{ background: `color-mix(in srgb, ${accent} 16%, transparent)`, color: accent }}
        >
          <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {data.name}
        </span>
      </div>
      {data.algorithm && (
        <p className="mt-1 truncate font-mono text-[11px]" style={{ color: "var(--text-muted)" }}>
          {data.algorithm}
        </p>
      )}
      {data.severity && (
        <span
          className="mt-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider"
          style={{
            background: `color-mix(in srgb, ${riskVar(data.severity)} 14%, transparent)`,
            color: riskVar(data.severity),
          }}
        >
          {data.severity}
        </span>
      )}
    </div>
  );
});
