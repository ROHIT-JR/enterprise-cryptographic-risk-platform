import { AlertTriangle, CheckCircle2, ChevronDown, Clock, FlaskConical, XCircle } from "lucide-react";
import type { ElementType } from "react";
import { useMemo, useState } from "react";
import { Card, EmptyState } from "./ui";
import type {
  MigrationVerification as Verification,
  MigrationVerificationReport,
  VerificationCheck,
  VerificationCheckStatus,
  VerificationOverall,
  VerificationTestResult,
} from "../types/api";

const PAGE_SIZE = 10;

const CHECK_STATUS: Record<VerificationCheckStatus, { label: string; icon: ElementType; text: string; bar: string }> = {
  pass: { label: "Pass", icon: CheckCircle2, text: "text-emerald-700", bar: "bg-emerald-500" },
  warn: { label: "Warning", icon: AlertTriangle, text: "text-amber-700", bar: "bg-amber-400" },
  fail: { label: "Fail", icon: XCircle, text: "text-red-700", bar: "bg-red-500" },
  pending: { label: "Pending", icon: Clock, text: "text-zinc-500", bar: "bg-zinc-300" },
};

const OVERALL: Record<VerificationOverall, { label: string; hint: string; chip: string; tile: string }> = {
  verified: {
    label: "Verified",
    hint: "Every check passed",
    chip: "border-emerald-300 bg-emerald-50 text-emerald-900",
    tile: "text-emerald-700",
  },
  conditional: {
    label: "Conditional",
    hint: "Passed with warnings",
    chip: "border-amber-300 bg-amber-50 text-amber-900",
    tile: "text-amber-700",
  },
  pending: {
    label: "Pending",
    hint: "Evidence still missing",
    chip: "border-zinc-300 bg-zinc-50 text-zinc-700",
    tile: "text-zinc-600",
  },
  blocked: {
    label: "Blocked",
    hint: "A check failed",
    chip: "border-red-300 bg-red-50 text-red-900",
    tile: "text-red-700",
  },
};
const OVERALL_ORDER: VerificationOverall[] = ["verified", "conditional", "pending", "blocked"];

const CHECK_LABELS: Record<string, string> = {
  algorithm_compatibility: "Algorithm compatibility",
  performance_threshold: "Performance within threshold",
  key_size: "Key size acceptable",
  backward_compatibility: "Backward compatibility",
  rollback_plan: "Rollback plan",
};

const BASIS_STYLE: Record<VerificationTestResult["basis"], string> = {
  benchmark: "border-zinc-300 bg-zinc-50 text-zinc-700",
  model: "border-sky-300 bg-sky-50 text-sky-900",
  simulated: "border-dashed border-amber-400 bg-amber-50 text-amber-900",
};

function StatusIcon({ status, className = "h-4 w-4" }: { status: VerificationCheckStatus; className?: string }) {
  const { icon: Icon, text } = CHECK_STATUS[status];
  return <Icon className={`${className} shrink-0 ${text}`} aria-hidden />;
}

function OverallChip({ overall }: { overall: VerificationOverall }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider ${OVERALL[overall].chip}`}
    >
      {OVERALL[overall].label}
    </span>
  );
}

// ─────────────────────────────────────────────
// Summary
// ─────────────────────────────────────────────
function SummaryTiles({
  summary,
  active,
  onSelect,
}: {
  summary: MigrationVerificationReport["summary"];
  active: VerificationOverall | "all";
  onSelect: (value: VerificationOverall | "all") => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5" role="group" aria-label="Filter migrations by verification status">
      <button
        type="button"
        aria-pressed={active === "all"}
        onClick={() => onSelect("all")}
        className={`rounded-md border p-3 text-left transition ${
          active === "all" ? "border-zinc-900 bg-zinc-900 text-white" : "border-zinc-200 bg-white hover:bg-zinc-50"
        }`}
      >
        <p className="font-mono text-[10px] uppercase tracking-wider opacity-70">All migrations</p>
        <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{summary.total}</p>
        <p className="text-[11px] opacity-70">Across all waves</p>
      </button>
      {OVERALL_ORDER.map((key) => (
        <button
          key={key}
          type="button"
          aria-pressed={active === key}
          onClick={() => onSelect(active === key ? "all" : key)}
          className={`rounded-md border p-3 text-left transition ${
            active === key ? "border-zinc-900 bg-zinc-50 ring-1 ring-zinc-900" : "border-zinc-200 bg-white hover:bg-zinc-50"
          }`}
        >
          <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">{OVERALL[key].label}</p>
          <p className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${OVERALL[key].tile}`}>{summary[key]}</p>
          <p className="text-[11px] text-zinc-500">{OVERALL[key].hint}</p>
        </button>
      ))}
    </div>
  );
}

function CheckCoverage({ summary }: { summary: MigrationVerificationReport["summary"] }) {
  const order: VerificationCheckStatus[] = ["pass", "warn", "fail", "pending"];
  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold text-zinc-950">Verification coverage</h2>
      <p className="mt-0.5 mb-3 text-[11px] text-zinc-500">How each of the five checks stands across all migration tasks.</p>
      <ul className="space-y-2">
        {Object.entries(CHECK_LABELS).map(([id, label]) => {
          const counts = summary.checks[id];
          if (!counts) return null;
          return (
            <li key={id} className="grid items-center gap-x-3 gap-y-1 sm:grid-cols-[13rem_1fr_auto]">
              <span className="text-xs text-zinc-800">{label}</span>
              <div
                className="flex h-2 overflow-hidden rounded-full bg-zinc-100"
                role="img"
                aria-label={order.map((s) => `${counts[s]} ${CHECK_STATUS[s].label.toLowerCase()}`).join(", ")}
              >
                {order.map((status) => (
                  <div
                    key={status}
                    className={CHECK_STATUS[status].bar}
                    style={{ width: `${summary.total ? (counts[status] / summary.total) * 100 : 0}%` }}
                  />
                ))}
              </div>
              <span className="font-mono text-[11px] text-zinc-500">
                {order
                  .filter((status) => counts[status] > 0)
                  .map((status) => `${counts[status]} ${CHECK_STATUS[status].label.toLowerCase()}`)
                  .join(" · ")}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// ─────────────────────────────────────────────
// Task card
// ─────────────────────────────────────────────
function Checklist({ checks }: { checks: VerificationCheck[] }) {
  return (
    <ul className="divide-y divide-zinc-100 rounded border border-zinc-200">
      {checks.map((check) => {
        const status = CHECK_STATUS[check.status];
        return (
          <li key={check.id} className="flex gap-3 p-3">
            <StatusIcon status={check.status} className="mt-0.5 h-4 w-4" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <p className="text-xs font-medium text-zinc-900">{check.title}</p>
                <span className={`font-mono text-[10px] uppercase tracking-wider ${status.text}`}>{status.label}</span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-400">{check.basis}</span>
              </div>
              <ul className="mt-1 space-y-0.5">
                {check.evidence.map((line) => (
                  <li key={line} className="text-[11px] leading-normal text-zinc-600">
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function HybridPath({ item }: { item: Verification }) {
  return (
    <ol className="grid gap-3 md:grid-cols-3">
      {item.hybrid_steps.map((step, index) => (
        <li key={step.step} className="relative rounded border border-zinc-200 bg-white p-3">
          <div className="flex items-start gap-2.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-mono text-[10px] font-semibold text-white">
              {step.step}
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold leading-snug text-zinc-950">{step.title}</p>
              <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-indigo-700">
                ~{step.duration_days} days
              </p>
            </div>
          </div>
          <p className="mt-2 text-[11px] leading-normal text-zinc-600">{step.description}</p>
          <p className="mt-2 text-[11px] leading-normal text-zinc-500">
            <span className="font-medium text-zinc-700">Exit criteria: </span>
            {step.exit_criteria}
          </p>
          {index < item.hybrid_steps.length - 1 && (
            <span
              aria-hidden
              className="absolute -right-2.5 top-6 z-10 hidden h-5 w-5 items-center justify-center rounded-full border border-zinc-200 bg-white text-[10px] text-zinc-400 md:flex"
            >
              →
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

function TestResults({ results }: { results: VerificationTestResult[] }) {
  return (
    <div className="overflow-x-auto rounded border border-zinc-200">
      <table className="w-full min-w-[640px] text-left text-xs">
        <caption className="sr-only">Test results for this migration</caption>
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
            <th scope="col" className="px-3 py-2 font-medium">Test</th>
            <th scope="col" className="px-3 py-2 font-medium">Measured</th>
            <th scope="col" className="px-3 py-2 font-medium">Threshold</th>
            <th scope="col" className="px-3 py-2 font-medium">Result</th>
            <th scope="col" className="px-3 py-2 font-medium">Basis</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => {
            const tone = result.status;
            const simulated = result.basis === "simulated";
            return (
              <tr key={result.id} className="border-b border-zinc-100 align-top last:border-0">
                <th scope="row" className="px-3 py-2 font-medium text-zinc-900">
                  {result.name}
                  {result.detail && (
                    <span className="mt-0.5 block font-normal text-[11px] leading-normal text-zinc-500">
                      {result.detail}
                    </span>
                  )}
                </th>
                <td className="px-3 py-2 font-mono tabular-nums text-zinc-800">{result.measured}</td>
                <td className="px-3 py-2 font-mono text-zinc-500">{result.threshold}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold uppercase ${CHECK_STATUS[tone].text} ${simulated ? "opacity-70" : ""}`}>
                    <StatusIcon status={tone} className="h-3.5 w-3.5" />
                    {result.status}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${BASIS_STYLE[result.basis]}`}>
                    {simulated && <FlaskConical className="h-3 w-3" aria-hidden />}
                    {result.basis}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TaskCard({ item }: { item: Verification }) {
  const [open, setOpen] = useState(false);
  const panelId = `verification-${item.asset_id}`;
  return (
    <Card>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 p-3 text-left sm:p-4"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-semibold text-zinc-950">{item.asset_name}</span>
            <span className="rounded border border-zinc-200 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
              {item.asset_type}
            </span>
            <span className="rounded border border-zinc-200 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
              wave {item.wave}
            </span>
          </div>
          <p className="mt-1 break-words font-mono text-[11px] text-zinc-600">
            {item.current_algorithm} <span aria-hidden>→</span>
            <span className="sr-only">migrates to</span> {item.recommended_algorithm}
          </p>
        </div>
        <div className="hidden items-center gap-1 sm:flex" aria-label="Check results">
          {item.checks.map((check) => (
            <span key={check.id} title={`${check.title}: ${CHECK_STATUS[check.status].label}`}>
              <StatusIcon status={check.status} className="h-3.5 w-3.5" />
              <span className="sr-only">
                {check.title}: {CHECK_STATUS[check.status].label}
              </span>
            </span>
          ))}
        </div>
        <OverallChip overall={item.overall} />
        <ChevronDown className={`h-4 w-4 shrink-0 text-zinc-400 transition ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>

      {open && (
        <div id={panelId} className="space-y-5 border-t border-zinc-100 p-3 sm:p-4">
          <section aria-labelledby={`${panelId}-checklist`}>
            <h3 id={`${panelId}-checklist`} className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Verification checklist
            </h3>
            <Checklist checks={item.checks} />
          </section>

          <section aria-labelledby={`${panelId}-hybrid`}>
            <h3 id={`${panelId}-hybrid`} className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Hybrid migration path
            </h3>
            <HybridPath item={item} />
          </section>

          <section aria-labelledby={`${panelId}-tests`}>
            <h3 id={`${panelId}-tests`} className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Test results
            </h3>
            <TestResults results={item.test_results} />
          </section>

          <section aria-labelledby={`${panelId}-rollback`}>
            <h3 id={`${panelId}-rollback`} className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Rollback plan
            </h3>
            <ol className="list-decimal space-y-1 pl-5 text-[11px] leading-normal text-zinc-600">
              {item.rollback_plan.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────
// Panel
// ─────────────────────────────────────────────
type KindFilter = "all" | Verification["target_kind"];

export function MigrationVerification({ report }: { report: MigrationVerificationReport }) {
  const [status, setStatus] = useState<VerificationOverall | "all">("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [visible, setVisible] = useState(PAGE_SIZE);

  const filtered = useMemo(
    () =>
      report.items
        .filter((item) => (status === "all" || item.overall === status) && (kind === "all" || item.target_kind === kind))
        // concrete algorithm migrations first: they carry the real evidence
        .sort((a, b) => Number(b.target_kind === "algorithm") - Number(a.target_kind === "algorithm")),
    [report.items, status, kind],
  );

  if (report.summary.total === 0) {
    return (
      <Card>
        <EmptyState
          title="No migration plans to verify"
          body="Upload and scan an environment first; verification runs on the generated migration plan."
        />
      </Card>
    );
  }

  const change = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value);
    setVisible(PAGE_SIZE);
  };

  return (
    <div className="space-y-5">
      <SummaryTiles summary={report.summary} active={status} onSelect={change(setStatus)} />

      <Card className="flex gap-3 border-indigo-200 bg-indigo-50/40 p-3">
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-indigo-700" aria-hidden />
        <p className="text-xs leading-normal text-zinc-700">
          Checklist status is <strong>computed</strong> from each plan&apos;s recommendation, the NIST knowledge base and
          the benchmark reference data, against the limits in{" "}
          <code className="font-mono">config/migration_verification.json</code> (per-operation{" "}
          {(report.thresholds.max_operation_us ?? 0) / 1000} ms, {(report.thresholds.max_wire_bytes ?? 0).toLocaleString("en")}{" "}
          B on the wire). Test results tagged <span className="font-mono">simulated</span> are illustrative placeholders
          and never count toward verification.
        </p>
      </Card>

      <CheckCoverage summary={report.summary} />

      <section aria-labelledby="tasks-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="tasks-heading" className="text-sm font-semibold text-zinc-950">
            Migration tasks{" "}
            <span className="font-mono text-xs font-normal text-zinc-500">
              ({filtered.length}
              {filtered.length !== report.summary.total ? ` of ${report.summary.total}` : ""})
            </span>
          </h2>
          <div className="inline-flex rounded border border-zinc-200 bg-white p-0.5" role="group" aria-label="Filter by target type">
            {(
              [
                ["all", "All"],
                ["algorithm", "Algorithms"],
                ["integration", "Applications & libraries"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={kind === value}
                onClick={() => change(setKind)(value)}
                className={`segment-tab rounded ${kind === value ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-50"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <Card>
            <EmptyState title="No migrations match these filters" body="Clear a filter to see more tasks." />
          </Card>
        ) : (
          <>
            {filtered.slice(0, visible).map((item) => (
              <TaskCard key={item.asset_id} item={item} />
            ))}
            {filtered.length > visible && (
              <button type="button" className="btn-secondary w-full" onClick={() => setVisible((count) => count + PAGE_SIZE)}>
                Show {Math.min(PAGE_SIZE, filtered.length - visible)} more ({filtered.length - visible} remaining)
              </button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
