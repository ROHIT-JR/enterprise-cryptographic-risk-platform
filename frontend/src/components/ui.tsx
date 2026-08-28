import type { HTMLAttributes, ReactNode } from "react";
import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { Severity } from "../types/api";
import { severityStyles } from "../utils/format";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-2xl border border-white/[0.07] bg-white/[0.035] shadow-panel backdrop-blur-sm ${className}`}
      {...props}
    />
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] ${severityStyles[severity]}`}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const style =
    status === "completed"
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
      : status === "failed"
        ? "border-rose-400/20 bg-rose-500/10 text-rose-300"
        : "border-brand-400/20 bg-brand-500/10 text-brand-300";
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] ${style}`}>
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
    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.24em] text-brand-300">{eyebrow}</p>
        <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function LoadingState({ label = "Loading cryptographic intelligence" }: { label?: string }) {
  return (
    <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
      <LoaderCircle className="h-5 w-5 animate-spin text-brand-400" />
      {label}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Card className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
      <span className="rounded-xl bg-rose-500/10 p-3 text-rose-300"><AlertTriangle className="h-6 w-6" /></span>
      <h2 className="mt-4 font-semibold text-white">Unable to load this view</h2>
      <p className="mt-2 max-w-md text-sm text-slate-400">{message}</p>
      {retry && (
        <button onClick={retry} className="mt-5 rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/5">
          Try again
        </button>
      )}
    </Card>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center px-6 text-center">
      <div className="h-2 w-2 rounded-full bg-brand-400 shadow-[0_0_20px_rgba(34,211,238,.8)]" />
      <h3 className="mt-4 font-medium text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">{body}</p>
    </div>
  );
}

