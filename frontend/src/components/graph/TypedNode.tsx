import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Building2, KeyRound, Lock, Package, Server, Shield, ShieldQuestion } from "lucide-react";
import type { Severity } from "../../types/api";

export type NodeShape = "circle" | "rounded-rect" | "diamond" | "hexagon";

export interface TypedNodeData {
  label: string;
  nodeType: string;
  severity?: Severity | null;
  quantumSafe?: boolean;
  degree: number;
  maxDegree: number;
  dimmed?: boolean;
  highlighted?: boolean;
  riskOverlay?: boolean;
  pulse?: boolean;
}

const TYPE_META: Record<string, { shape: NodeShape; icon: typeof Server; color: (d: TypedNodeData) => string }> = {
  project: { shape: "circle", icon: Building2, color: () => "var(--accent)" },
  organization: { shape: "circle", icon: Building2, color: () => "var(--accent)" },
  application: { shape: "rounded-rect", icon: Server, color: (d) => (d.severity ? `var(--risk-${d.severity})` : "var(--text-muted)") },
  service: { shape: "rounded-rect", icon: Server, color: (d) => (d.severity ? `var(--risk-${d.severity})` : "var(--text-muted)") },
  algorithm: { shape: "circle", icon: KeyRound, color: (d) => (d.quantumSafe ? "var(--risk-low)" : "var(--risk-critical)") },
  library: { shape: "rounded-rect", icon: Package, color: () => "var(--tint-library)" },
  certificate: { shape: "diamond", icon: Shield, color: () => "var(--tint-certificate)" },
  protocol: { shape: "hexagon", icon: Lock, color: () => "var(--tint-protocol)" },
  configuration: { shape: "rounded-rect", icon: ShieldQuestion, color: () => "var(--text-muted)" },
};

const CLIP_PATH: Record<NodeShape, string | undefined> = {
  circle: undefined,
  "rounded-rect": undefined,
  diamond: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
  hexagon: "polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)",
};

export const TypedNode = memo(function TypedNode({ data }: NodeProps<TypedNodeData>) {
  const meta = TYPE_META[data.nodeType] ?? TYPE_META.configuration!;
  const Icon = meta.icon;
  const color = meta.color(data);
  const sizeRatio = data.maxDegree > 0 ? data.degree / data.maxDegree : 0;
  const size = meta.shape === "circle" ? 56 + Math.round(sizeRatio * 24) : undefined;
  const isCompact = meta.shape === "circle" || meta.shape === "diamond" || meta.shape === "hexagon";

  const borderColor = data.riskOverlay && data.severity ? `var(--risk-${data.severity})` : color;
  const opacity = data.dimmed ? 0.2 : 1;

  return (
    <div
      className={`interactive flex items-center justify-center border-2 text-center ${data.pulse ? "animate-pulse-glow-red" : ""}`}
      style={{
        width: size ?? (150 + Math.round(sizeRatio * 60)),
        height: size ?? 52,
        borderRadius: meta.shape === "circle" ? "50%" : meta.shape === "rounded-rect" ? 10 : 0,
        clipPath: CLIP_PATH[meta.shape],
        borderColor,
        background: data.highlighted ? `color-mix(in srgb, ${color} 18%, var(--bg-card))` : "var(--bg-card)",
        opacity,
        boxShadow: data.highlighted ? `0 0 0 2px ${color}` : "none",
        transition: "opacity 250ms ease, box-shadow 250ms ease, border-color 250ms ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: "var(--border-strong)", opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "var(--border-strong)", opacity: 0 }} />
      <div className={`flex flex-col items-center gap-0.5 px-1.5 ${isCompact ? "" : "py-1"}`}>
        <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} />
        <span
          className="truncate font-medium leading-tight"
          style={{ color: "var(--text-primary)", fontSize: isCompact ? 9 : 11, maxWidth: size ? size - 16 : 130 }}
        >
          {data.label}
        </span>
      </div>
    </div>
  );
});
