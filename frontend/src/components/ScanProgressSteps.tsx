import { motion, AnimatePresence } from "motion/react";
import { Loader2, Check } from "lucide-react";
import { cn } from "../utils/cn";
import type { ScanProgressEvent } from "../hooks/useScanProgress";

export type ScanStepStatus = "pending" | "active" | "done";

export interface ScanStep {
  id: string;
  title: string;
  status: ScanStepStatus;
  progress: number; // 0-100, this step's own fill
}

/**
 * Adapted from shadcndashboard.dev's AnimatedList "Setup Steps" pattern
 * (components/animated-list/animated-list-02.tsx): checkmark + full bar for
 * done, spinner + partial bar for active, muted + empty bar for pending.
 *
 * Unlike the shadcn demo (which auto-cycles a fixed list on a setInterval),
 * this is driven by real backend progress — see deriveScanSteps() below,
 * which maps the SSE stage checkpoints emitted by
 * backend/app/services/orchestrator.py onto four canonical steps.
 */
export function ScanProgressSteps({ steps }: { steps: ScanStep[] }) {
  return (
    <div className="flex flex-col gap-2">
      <AnimatePresence initial={false}>
        {steps.map((step) => (
          <motion.div
            key={step.id}
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: step.status === "pending" ? 0.55 : 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className={cn("rounded-lg border p-3")}
            style={{
              background: "var(--bg-card)",
              borderColor: step.status === "active" ? "var(--accent)" : "var(--border)",
            }}
          >
            <div className="flex items-center gap-2">
              {step.status === "done" && <Check className="h-4 w-4 shrink-0" style={{ color: "var(--risk-low)" }} />}
              {step.status === "active" && <Loader2 className="h-4 w-4 shrink-0 animate-spin" style={{ color: "var(--accent)" }} />}
              {step.status === "pending" && <span className="h-4 w-4 shrink-0 rounded-full border" style={{ borderColor: "var(--border-strong)" }} />}
              <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{step.title}</span>
            </div>
            <div className="mt-2 h-1 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
              <div
                className="h-1 rounded-full transition-all duration-300"
                style={{ width: `${step.progress}%`, background: "var(--risk-low)" }}
              />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/**
 * Canonical checkpoints, taken directly from the `publish(scan.id, {...})`
 * calls in backend/app/services/orchestrator.py — not guessed:
 *   10  "Scan started"
 *   20  "Scanning {source_type} target..."
 *   45  "Discovered N candidate assets, persisting..."
 *   65  "Calculating risk scores..."
 *   70  "Analyzing quantum risk intelligence..."
 *   78  "Generating CBOM..."
 *   88  "Syncing knowledge graph..."
 *   100 completed
 */
const STEP_BANDS: { id: string; title: string; from: number; to: number }[] = [
  { id: "discover", title: "Connecting & scanning target", from: 0, to: 20 },
  { id: "extract", title: "Extracting cryptographic assets", from: 20, to: 45 },
  { id: "risk", title: "Calculating risk & quantum exposure", from: 45, to: 70 },
  { id: "cbom", title: "Generating CBOM & syncing graph", from: 70, to: 100 },
];

export function deriveScanSteps(progress: number | null, done: boolean, failed: boolean): ScanStep[] {
  const effectiveProgress = done ? 100 : (progress ?? 0);
  return STEP_BANDS.map((band) => {
    let status: ScanStepStatus = "pending";
    let stepProgress = 0;
    if (effectiveProgress >= band.to || (done && !failed)) {
      status = "done";
      stepProgress = 100;
    } else if (effectiveProgress > band.from) {
      status = "active";
      stepProgress = Math.round(((effectiveProgress - band.from) / (band.to - band.from)) * 100);
    }
    return { id: band.id, title: band.title, status, progress: stepProgress };
  });
}

/** Convenience: derive directly from useScanProgress's raw event stream. */
export function deriveScanStepsFromEvents(events: ScanProgressEvent[], liveProgress: number | null): ScanStep[] {
  const failed = events.some((e) => e.type === "failed");
  const completed = events.some((e) => e.type === "completed");
  return deriveScanSteps(liveProgress, completed, failed);
}
