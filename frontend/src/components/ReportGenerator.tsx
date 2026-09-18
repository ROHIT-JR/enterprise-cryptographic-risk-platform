import {
  AlertCircle,
  Atom,
  Boxes,
  CheckCircle2,
  Download,
  FileCheck2,
  Loader2,
  Route,
  ScrollText,
  ShieldAlert,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import {
  apiReportErrorMessage,
  enterpriseApi,
  reportFilename,
  type ReportFormat,
  type ReportType,
} from "../api/client";

interface FormatChoice {
  id: string;
  label: string;
  formats: ReportFormat[];
}

type Choices = [FormatChoice, ...FormatChoice[]];

interface ReportOption {
  key: string;
  type: ReportType;
  label: string;
  description: string;
  icon: LucideIcon;
  choices: Choices;
}

const PDF_OR_JSON: Choices = [
  { id: "pdf", label: "PDF", formats: ["pdf"] },
  { id: "json", label: "JSON", formats: ["json"] },
];

const EXECUTIVE_SUMMARY: ReportOption = {
  key: "executive-summary",
  type: "executive-summary",
  label: "Executive summary",
  description: "One page for leadership: risk gauge, key metrics, top 5 critical assets, Mosca status.",
  icon: ShieldAlert,
  choices: PDF_OR_JSON,
};

export const REPORT_OPTIONS: ReportOption[] = [
  EXECUTIVE_SUMMARY,
  {
    key: "technical",
    type: "technical",
    label: "Technical report",
    description: "Full inventory, risk breakdown, dependency graph, roadmap, PQC matrix and CBOM summary.",
    icon: ScrollText,
    choices: PDF_OR_JSON,
  },
  {
    key: "cbom",
    type: "inventory",
    label: "CBOM (CycloneDX 1.6)",
    description: "Cryptography bill of materials with risk scores. Machine-readable JSON, human-readable PDF, or both.",
    icon: FileCheck2,
    choices: [
      { id: "cbom", label: "CycloneDX JSON", formats: ["cbom"] },
      { id: "cbom-pdf", label: "PDF", formats: ["cbom-pdf"] },
      { id: "both", label: "Both", formats: ["cbom", "cbom-pdf"] },
    ],
  },
  {
    key: "inventory",
    type: "inventory",
    label: "Asset inventory",
    description: "Every discovered cryptographic asset with algorithm, version and location.",
    icon: Boxes,
    choices: PDF_OR_JSON,
  },
  {
    key: "quantum-risk",
    type: "quantum-risk",
    label: "Quantum risk",
    description: "Per-asset ECDAT score, severity, HNDL exposure and dependent systems.",
    icon: Atom,
    choices: PDF_OR_JSON,
  },
  {
    key: "migration",
    type: "migration",
    label: "Migration plan",
    description: "Wave-ordered PQC migration plan with recommended algorithms and complexity.",
    icon: Route,
    choices: PDF_OR_JSON,
  },
];

function findOption(key: string): ReportOption {
  return REPORT_OPTIONS.find((item) => item.key === key) ?? EXECUTIVE_SUMMARY;
}

type Status =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "done"; files: string[] }
  | { kind: "error"; message: string };

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function ReportGenerator({
  open,
  onClose,
  initialKey = "executive-summary",
}: {
  open: boolean;
  onClose: () => void;
  initialKey?: string;
}) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const [reportKey, setReportKey] = useState(initialKey);
  const [choiceId, setChoiceId] = useState("pdf");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const option = findOption(reportKey);
  const choice = option.choices.find((item) => item.id === choiceId) ?? option.choices[0];
  const working = status.kind === "working";

  useEffect(() => {
    if (!open) return;
    const requested = findOption(initialKey);
    setReportKey(requested.key);
    setChoiceId(requested.choices[0].id);
    setStatus({ kind: "idle" });
    const previous = document.activeElement as HTMLElement | null;
    panelRef.current?.querySelector<HTMLElement>("input[type=radio]:checked")?.focus();
    return () => previous?.focus?.();
  }, [open, initialKey]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  function selectReport(next: ReportOption) {
    setReportKey(next.key);
    setChoiceId(next.choices[0].id);
    setStatus({ kind: "idle" });
  }

  async function generate() {
    setStatus({ kind: "working" });
    const files: string[] = [];
    try {
      for (const format of choice.formats) {
        const blob = await enterpriseApi.report(option.type, format);
        const filename = reportFilename(option.type, format);
        saveBlob(blob, filename);
        files.push(filename);
      }
      setStatus({ kind: "done", files });
    } catch (caught) {
      setStatus({ kind: "error", message: await apiReportErrorMessage(caught) });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Close report generator"
        className="absolute inset-0 cursor-default bg-zinc-950/40"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="animate-fade-in relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-md border border-zinc-200 bg-white shadow-popover"
      >
        <div className="flex items-start justify-between gap-4 border-b border-zinc-200 px-5 py-4">
          <div>
            <h2 id={titleId} className="text-sm font-bold text-zinc-950">
              Generate report
            </h2>
            <p className="mt-0.5 text-xs text-zinc-500">
              Branded, printable exports for your organization. Every download is recorded in the audit log.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-5 overflow-y-auto px-5 py-4">
          <fieldset>
            <legend className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Report
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {REPORT_OPTIONS.map((item) => {
                const selected = item.key === option.key;
                const Icon = item.icon;
                return (
                  <label
                    key={item.key}
                    className={`flex cursor-pointer gap-3 rounded border p-3 transition focus-within:ring-2 focus-within:ring-indigo-600/40 ${
                      selected
                        ? "border-indigo-600 bg-indigo-50/60"
                        : "border-zinc-200 hover:border-zinc-400 hover:bg-zinc-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="report"
                      className="sr-only"
                      checked={selected}
                      onChange={() => selectReport(item)}
                      disabled={working}
                    />
                    <span
                      className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded border ${
                        selected ? "border-indigo-200 bg-white text-indigo-600" : "border-zinc-200 bg-zinc-50 text-zinc-600"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-xs font-semibold text-zinc-950">{item.label}</span>
                      <span className="mt-0.5 block text-[11px] leading-snug text-zinc-500">{item.description}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <fieldset>
            <legend className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Format
            </legend>
            <div className="flex flex-wrap gap-2">
              {option.choices.map((item) => {
                const selected = item.id === choice.id;
                return (
                  <label
                    key={item.id}
                    className={`cursor-pointer rounded border px-3 py-1.5 text-xs font-medium transition focus-within:ring-2 focus-within:ring-indigo-600/40 ${
                      selected
                        ? "border-indigo-600 bg-indigo-600 text-white"
                        : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="format"
                      className="sr-only"
                      checked={selected}
                      onChange={() => {
                        setChoiceId(item.id);
                        setStatus({ kind: "idle" });
                      }}
                      disabled={working}
                    />
                    {item.label}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div role="status" aria-live="polite" className="min-h-5 text-xs">
            {status.kind === "working" && (
              <p className="flex items-center gap-2 text-zinc-600">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Building {option.label.toLowerCase()}...
              </p>
            )}
            {status.kind === "done" && (
              <p className="flex items-start gap-2 text-emerald-700">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Downloaded <span className="font-mono">{status.files.join(", ")}</span>
                </span>
              </p>
            )}
            {status.kind === "error" && (
              <p className="flex items-start gap-2 text-red-700">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{status.message}</span>
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-zinc-200 bg-zinc-50 px-5 py-3">
          <button type="button" className="btn-secondary" onClick={onClose}>
            {status.kind === "done" ? "Close" : "Cancel"}
          </button>
          <button type="button" className="btn-primary" onClick={() => void generate()} disabled={working}>
            {working ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            {working ? "Generating..." : "Download"}
          </button>
        </div>
      </div>
    </div>
  );
}
