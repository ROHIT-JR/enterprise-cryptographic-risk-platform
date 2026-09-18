import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import type { Severity } from "../types/api";
import { severityStyles } from "../utils/format";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-md border border-zinc-200 bg-white shadow-subtle ${className}`}
      {...props}
    />
  );
}

export function CardHeader({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`px-4 py-3 border-b border-zinc-100 flex items-center justify-between ${className}`} {...props} />;
}

export function CardTitle({ className = "", ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={`text-xs font-mono font-semibold uppercase tracking-wider text-zinc-900 ${className}`} {...props} />;
}

export function CardContent({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`p-4 ${className}`} {...props} />;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider border ${severityStyles[severity]}`}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const style =
    status === "completed"
      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
      : status === "failed"
        ? "border-red-300 bg-red-50 text-red-900"
        : "border-zinc-300 bg-zinc-50 text-zinc-900";
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider border ${style}`}>
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
    <div className="flex flex-col gap-3 pb-2 md:flex-row md:items-end md:justify-between border-b border-zinc-200/80">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
          <p className="font-mono text-[10px] font-medium uppercase tracking-widest text-zinc-500">{eyebrow}</p>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-950 font-sans">{title}</h1>
        <p className="mt-1 text-xs text-zinc-500 leading-normal max-w-2xl">{description}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading cryptographic intelligence telemetry" }: { label?: string }) {
  return (
    <div className="flex min-h-56 items-center justify-center gap-2 text-xs font-mono text-zinc-500">
      <Loader2 className="h-4 w-4 animate-spin text-zinc-700" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Card className="flex min-h-48 flex-col items-center justify-center p-6 text-center border-red-200/80">
      <AlertCircle className="h-5 w-5 text-red-600 mb-2" />
      <h2 className="text-sm font-semibold text-zinc-950">Intake / Query Execution Failed</h2>
      <p className="mt-1 max-w-md font-mono text-xs text-zinc-600">{message}</p>
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
      <div className="h-1 w-6 bg-zinc-300 mb-2.5 rounded-full" />
      <h3 className="text-xs font-medium text-zinc-800">{title}</h3>
      <p className="mt-1 max-w-xs text-[11px] text-zinc-500 leading-normal">{body}</p>
    </div>
  );
}
