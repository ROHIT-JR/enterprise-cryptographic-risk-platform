import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import type { Severity } from "../types/api";
import { severityStyles } from "../utils/format";

export function Card({ className = "", style, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border shadow-subtle transition-all duration-200 ${className}`}
      style={{ background: "var(--bg-card)", borderColor: "var(--border)", ...style }}
      {...props}
    />
  );
}

export function CardHeader({ className = "", style, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`flex items-center justify-between px-4 py-3 ${className}`}
      style={{ borderBottom: "1px solid var(--border)", ...style }}
      {...props}
    />
  );
}

export function CardTitle({ className = "", style, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={`text-xs font-mono font-semibold uppercase tracking-wider ${className}`}
      style={{ color: "var(--text-primary)", ...style }}
      {...props}
    />
  );
}

export function CardContent({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`p-4 ${className}`} {...props} />;
}

const severityGlow: Record<Severity, string> = {
  critical: "0 0 0 3px color-mix(in srgb, var(--risk-critical) 12%, transparent)",
  high:     "0 0 0 3px color-mix(in srgb, var(--risk-high) 12%, transparent)",
  medium:   "0 0 0 3px color-mix(in srgb, var(--risk-medium) 12%, transparent)",
  low:      "0 0 0 3px color-mix(in srgb, var(--risk-low) 12%, transparent)",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider border ${severityStyles[severity]}`}
      style={{ boxShadow: severityGlow[severity] }}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const style =
    status === "completed"
      ? "border-[var(--risk-low)]/35 bg-[var(--risk-low)]/10 text-[var(--risk-low)]"
      : status === "failed"
        ? "border-[var(--risk-critical)]/35 bg-[var(--risk-critical)]/10 text-[var(--risk-critical)]"
        : "border-[var(--border)] text-[var(--text-secondary)]";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider border ${style}`}
      style={status !== "completed" && status !== "failed" ? { background: "var(--bg-hover)" } : undefined}
    >
      {status}
    </span>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div
      className="flex flex-col gap-3 pb-4 md:flex-row md:items-end md:justify-between"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--accent)" }} />
          <p className="font-mono text-[10px] font-medium uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            {eyebrow}
          </p>
        </div>
        <h1 className="text-xl font-bold tracking-tight font-sans" style={{ color: "var(--text-primary)" }}>
          {title}
        </h1>
        <p className="mt-1 text-xs leading-normal max-w-2xl" style={{ color: "var(--text-muted)" }}>
          {description}
        </p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading cryptographic intelligence telemetry" }: { label?: string }) {
  return (
    <div className="flex min-h-56 items-center justify-center gap-2 text-xs font-mono" style={{ color: "var(--text-muted)" }}>
      <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--text-secondary)" }} />
      <span>{label}</span>
    </div>
  );
}

function SkeletonBlock({ className = "" }: { className?: string }) {
  return (
    <div
      className={`shimmer rounded-xl ${className}`}
      style={{ background: "var(--bg-hover)" }}
    />
  );
}

/**
 * Shimmer skeleton for whole-page loading states (issue #73) — replaces a
 * bare spinner with a layout-shaped placeholder so the page doesn't visually
 * "pop" once data arrives. `rows` controls how many list/table rows to fake
 * below the header + KPI-card placeholders.
 */
export function PageSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <SkeletonBlock className="h-3 w-32" />
          <SkeletonBlock className="h-6 w-64" />
        </div>
        <SkeletonBlock className="h-9 w-36" />
      </div>
      <div className="stagger grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => <SkeletonBlock key={i} className="h-24" />)}
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }, (_, i) => <SkeletonBlock key={i} className="h-14" />)}
      </div>
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Card className="flex min-h-48 flex-col items-center justify-center p-6 text-center" style={{ borderColor: "var(--risk-critical)", opacity: 0.94 }}>
      <AlertCircle className="h-5 w-5 mb-2" style={{ color: "var(--risk-critical)" }} />
      <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Intake / Query Execution Failed</h2>
      <p className="mt-1 max-w-md font-mono text-xs" style={{ color: "var(--text-muted)" }}>{message}</p>
      {retry && (
        <button onClick={retry} className="btn-secondary mt-4">
          Retry telemetry query
        </button>
      )}
    </Card>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex min-h-44 flex-col items-center justify-center p-6 text-center">
      <div className="h-1 w-6 mb-2.5 rounded-full" style={{ background: "var(--border-strong)" }} />
      <h3 className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{title}</h3>
      <p className="mt-1 max-w-xs text-[11px] leading-normal" style={{ color: "var(--text-muted)" }}>{body}</p>
    </div>
  );
}

export interface RadialGaugeSegment {
  label: string;
  value: number;
  color: string;
}

/**
 * Tick-mark radial gauge matching the shadcn health-dashboard reference's
 * "Department Stats" widget: a ring built from many small ticks (not a
 * solid conic arc), colored proportionally by each segment's share of the
 * total, with a centered icon + number + label.
 */
export function RadialGauge({
  segments,
  centerValue,
  centerLabel,
  icon,
  size = 176,
  tickCount = 48,
}: {
  segments: RadialGaugeSegment[];
  centerValue: ReactNode;
  centerLabel: string;
  icon?: ReactNode;
  size?: number;
  tickCount?: number;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  // Build a flat array of tickCount colors, proportioned by each segment's share of the total.
  const tickColors: string[] = [];
  if (total > 0) {
    let remainder = 0;
    for (const segment of segments) {
      const exact = (segment.value / total) * tickCount + remainder;
      const count = Math.round(exact);
      remainder = exact - count;
      for (let i = 0; i < count; i++) tickColors.push(segment.color);
    }
  }
  while (tickColors.length < tickCount) tickColors.push("var(--border-strong)");

  const radius = size / 2;
  const tickLength = size * 0.09;
  const tickWidth = Math.max(1.5, size * 0.012);

  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
        {tickColors.slice(0, tickCount).map((color, index) => {
          const angle = (360 / tickCount) * index;
          return (
            <rect
              key={index}
              x={radius - tickWidth / 2}
              y={2}
              width={tickWidth}
              height={tickLength}
              rx={tickWidth / 2}
              fill={color}
              opacity={total > 0 ? 1 : 0.35}
              transform={`rotate(${angle} ${radius} ${radius})`}
            />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {icon && (
          <div
            className="mb-1 flex h-7 w-7 items-center justify-center rounded-full"
            style={{ background: "var(--bg-hover)", color: "var(--text-secondary)" }}
          >
            {icon}
          </div>
        )}
        <p className="tabular-nums font-mono text-xl font-bold" style={{ color: "var(--text-primary)" }}>{centerValue}</p>
        <p className="font-mono text-[9px] uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>{centerLabel}</p>
      </div>
    </div>
  );
}

/**
 * Thin inline sparkline — a bare Recharts AreaChart with no axes, ~60px
 * tall, for KPI cards that have a real per-point series to show. Not wired
 * into fabricated/placeholder trend data anywhere — the dashboard API does
 * not currently return a time series, so this is provided for pages/future
 * endpoints that do have one rather than left unbuilt.
 */
export function Sparkline({
  data,
  color = "var(--accent)",
  height = 60,
}: {
  data: number[];
  color?: string;
  height?: number;
}) {
  const points = data.map((value, index) => ({ index, value }));
  const gradientId = `sparkline-${color.replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} fill={`url(#${gradientId})`} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
