import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
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

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider border ${severityStyles[severity]}`}
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
