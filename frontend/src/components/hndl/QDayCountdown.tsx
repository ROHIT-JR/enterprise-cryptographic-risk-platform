import { CalendarClock } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuFieldTrigger, DropdownMenuItem } from "../DropdownMenu";

export type QDayScenario = "optimistic" | "moderate" | "pessimistic" | "custom";

const SCENARIO_LABELS: Record<QDayScenario, string> = {
  optimistic: "Optimistic",
  moderate: "Moderate",
  pessimistic: "Pessimistic",
  custom: "Custom",
};

const CURRENT_YEAR = new Date().getFullYear();
// Heuristic lead time assumed for a migration project to complete before
// Q-Day — same style of documented heuristic as estimateDataLifetime()
// in QuantumRiskDashboard.tsx, since we don't have a per-org migration
// velocity figure to compute this from.
const MIGRATION_LEAD_YEARS = 3;

function bandColor(yearsRemaining: number): { border: string; bg: string; text: string; pulse: boolean } {
  if (yearsRemaining < 0) return { border: "var(--risk-critical)", bg: "color-mix(in srgb, var(--risk-critical) 12%, transparent)", text: "var(--risk-critical)", pulse: true };
  if (yearsRemaining < 5) return { border: "var(--risk-critical)", bg: "color-mix(in srgb, var(--risk-critical) 8%, transparent)", text: "var(--risk-critical)", pulse: false };
  if (yearsRemaining <= 10) return { border: "var(--risk-medium)", bg: "color-mix(in srgb, var(--risk-medium) 8%, transparent)", text: "var(--risk-medium)", pulse: false };
  return { border: "var(--risk-low)", bg: "color-mix(in srgb, var(--risk-low) 8%, transparent)", text: "var(--risk-low)", pulse: false };
}

export function QDayCountdown({
  scenario,
  onScenarioChange,
  quantumYear,
  customYear,
  onCustomYearChange,
}: {
  scenario: QDayScenario;
  onScenarioChange: (scenario: QDayScenario) => void;
  quantumYear: number;
  customYear: number;
  onCustomYearChange: (year: number) => void;
}) {
  const deadlineYear = quantumYear - MIGRATION_LEAD_YEARS;
  const yearsToDeadline = deadlineYear - CURRENT_YEAR;
  const band = bandColor(yearsToDeadline);

  const timelineStart = CURRENT_YEAR;
  const timelineEnd = Math.max(quantumYear + 2, CURRENT_YEAR + 5);
  const span = timelineEnd - timelineStart;
  const deadlinePct = Math.min(100, Math.max(0, ((deadlineYear - timelineStart) / span) * 100));
  const quantumPct = Math.min(100, Math.max(0, ((quantumYear - timelineStart) / span) * 100));

  return (
    <div
      className={`rounded-xl border p-5 ${band.pulse ? "animate-pulse-glow-red" : ""}`}
      style={{ borderColor: band.border, background: band.bg }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <CalendarClock className="h-5 w-5" style={{ color: band.text }} />
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-widest" style={{ color: band.text }}>
              Quantum Threat Timeline
            </p>
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Estimated Q-Day: <strong>{quantumYear}</strong> — Your Deadline: <strong>{deadlineYear}</strong>
            </p>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuFieldTrigger className="w-48">
            Quantum arrival: {SCENARIO_LABELS[scenario]}
          </DropdownMenuFieldTrigger>
          <DropdownMenuContent>
            {(Object.keys(SCENARIO_LABELS) as QDayScenario[]).map((option) => (
              <DropdownMenuItem key={option} selected={option === scenario} onSelect={() => onScenarioChange(option)}>
                {SCENARIO_LABELS[option]}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {scenario === "custom" && (
        <div className="mt-3 flex items-center gap-2">
          <label className="text-xs" style={{ color: "var(--text-muted)" }}>Custom quantum arrival year:</label>
          <input
            type="number"
            min={CURRENT_YEAR + 1}
            max={CURRENT_YEAR + 40}
            value={customYear}
            onChange={(e) => onCustomYearChange(Number(e.target.value))}
            className="field !w-24 !py-1"
          />
        </div>
      )}

      {/* Horizontal progress track: today -> deadline -> quantum arrival */}
      <div className="relative mt-4 h-2 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${deadlinePct}%`, background: band.text }} />
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2"
          style={{ left: `${deadlinePct}%`, transform: "translate(-50%, -50%)", borderColor: band.text, background: "var(--bg-card)" }}
          title={`Migration deadline: ${deadlineYear}`}
        />
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2"
          style={{ left: `${quantumPct}%`, transform: "translate(-50%, -50%)", borderColor: "var(--risk-critical)", background: "var(--bg-card)" }}
          title={`Quantum arrival: ${quantumYear}`}
        />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
        <span>{timelineStart} (today)</span>
        <span>{deadlineYear} (must migrate by)</span>
        <span>{quantumYear} (quantum arrives)</span>
      </div>

      <p className="mt-3 text-xs" style={{ color: band.text }}>
        {yearsToDeadline < 0
          ? `Deadline passed ${Math.abs(yearsToDeadline)} years ago — migration is overdue.`
          : `You have approximately ${yearsToDeadline} years to complete migration.`}
        <span style={{ color: "var(--text-muted)" }}> Based on: assumed {MIGRATION_LEAD_YEARS}-year migration lead time before Q-Day.</span>
      </p>
    </div>
  );
}
