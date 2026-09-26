import type { MigrationRoadmap } from "../../types/api";

// Assumed team throughput used to convert real per-item estimated_hours
// (backend/app/api/migration.py) into a wave schedule. Documented heuristic,
// not a measured velocity — same role as the effort-hours heuristic itself.
const TEAM_SIZE = 2;
const HOURS_PER_ENGINEER_PER_MONTH = 160;
const TEAM_CAPACITY_PER_MONTH = TEAM_SIZE * HOURS_PER_ENGINEER_PER_MONTH;

const WAVE_COLOR: Record<number, string> = {
  1: "var(--risk-low)",
  2: "var(--accent)",
  3: "var(--tint-library)",
};

export interface WaveSchedule {
  wave: number;
  title: string;
  totalHours: number;
  startMonth: number;
  endMonth: number;
}

export function computeWaveSchedule(waves: MigrationRoadmap["waves"]): WaveSchedule[] {
  let cursor = 0;
  return [...waves]
    .sort((a, b) => a.wave - b.wave)
    .map((wave) => {
      const totalHours = wave.items.reduce((sum, item) => sum + item.estimated_hours, 0);
      const durationMonths = Math.max(1, Math.ceil(totalHours / TEAM_CAPACITY_PER_MONTH));
      const startMonth = cursor;
      const endMonth = startMonth + durationMonths;
      cursor = endMonth;
      return { wave: wave.wave, title: wave.title, totalHours, startMonth, endMonth };
    });
}

const LABEL_WIDTH = "8rem";

export function GanttChart({
  schedule,
  qDayMonth,
  selectedWave,
  onSelectWave,
}: {
  schedule: WaveSchedule[];
  qDayMonth: number;
  selectedWave: number | null;
  onSelectWave: (wave: number | null) => void;
}) {
  const totalMonths = Math.max(qDayMonth + 2, schedule.at(-1)?.endMonth ?? 1, 6);

  return (
    <div>
      {/* Month axis */}
      <div className="mb-1 flex font-mono text-[9px]" style={{ paddingLeft: LABEL_WIDTH, color: "var(--text-muted)" }}>
        {Array.from({ length: totalMonths }, (_, i) => i + 1).map((m) => (
          <div key={m} className="flex-1 text-center">{m % 3 === 0 || m === 1 ? m : ""}</div>
        ))}
      </div>

      <div className="space-y-2.5">
        {schedule.map((wave, index) => {
          const isSelected = selectedWave === wave.wave;
          const left = (wave.startMonth / totalMonths) * 100;
          const width = ((wave.endMonth - wave.startMonth) / totalMonths) * 100;
          const color = WAVE_COLOR[wave.wave] ?? "var(--text-muted)";
          const prevWave = index > 0 ? schedule[index - 1] : null;
          return (
            <div key={wave.wave} className="flex items-center gap-3">
              <button
                className="interactive shrink-0 text-left"
                style={{ width: LABEL_WIDTH }}
                onClick={() => onSelectWave(isSelected ? null : wave.wave)}
              >
                <p className="text-xs font-bold" style={{ color }}>Wave {wave.wave}</p>
                <p className="truncate text-[11px]" style={{ color: "var(--text-muted)" }}>{wave.title}</p>
              </button>

              {/* Track — the only element percentages below are relative to */}
              <div
                className="relative h-9 flex-1 overflow-visible rounded-lg border"
                style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}
              >
                {/* Q-Day marker, only drawn once (on the first row) so it doesn't repeat, but spans all rows visually via a tall line */}
                {index === 0 && (
                  <div
                    className="pointer-events-none absolute z-10 border-l-2"
                    style={{
                      left: `${(qDayMonth / totalMonths) * 100}%`,
                      top: 0,
                      height: `${schedule.length * 44 + (schedule.length - 1) * 10}px`,
                      borderColor: "var(--risk-critical)",
                    }}
                  >
                    <span
                      className="-mt-1 ml-0.5 whitespace-nowrap rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider"
                      style={{ background: "var(--risk-critical)", color: "var(--text-on-accent)" }}
                    >
                      Q-Day
                    </span>
                  </div>
                )}

                {/* Dependency arrow from the previous wave's end to this wave's start */}
                {prevWave && (
                  <svg className="pointer-events-none absolute -top-3 left-0 h-3 w-full overflow-visible">
                    <line
                      x1={`${(prevWave.endMonth / totalMonths) * 100}%`}
                      y1={0}
                      x2={`${left}%`}
                      y2={12}
                      stroke={color}
                      strokeWidth={1.5}
                      strokeDasharray="3 2"
                      markerEnd="url(#gantt-arrow)"
                    />
                  </svg>
                )}

                <button
                  className="interactive card-hover absolute inset-y-1 rounded-md border"
                  style={{
                    left: `${left}%`,
                    width: `${Math.max(width, 2)}%`,
                    background: `color-mix(in srgb, ${color} 14%, var(--bg-card))`,
                    borderColor: color,
                    boxShadow: isSelected ? `0 0 0 2px ${color}` : "none",
                  }}
                  onClick={() => onSelectWave(isSelected ? null : wave.wave)}
                  title={`Months ${wave.startMonth + 1}–${wave.endMonth} · ${wave.totalHours}h — depends on: ${prevWave ? `Wave ${prevWave.wave}` : "none (foundation layer)"}`}
                />
                {/* Label sits next to the bar rather than inside it — Q-Day can be
                    years past a short migration window, which shrinks the bar to a
                    sliver too narrow to hold its own text (found via live visual
                    check: "Months 3-9 · 22h" was clipped mid-word inside a ~6%-wide
                    bar). An external label is legible at any bar width. */}
                <span
                  className="pointer-events-none absolute top-1/2 -translate-y-1/2 whitespace-nowrap text-[11px] font-semibold"
                  style={{ left: `calc(${left}% + ${Math.max(width, 2)}% + 8px)`, color }}
                >
                  Months {wave.startMonth + 1}–{wave.endMonth} · {wave.totalHours}h
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <svg width="0" height="0">
        <defs>
          <marker id="gantt-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill="var(--text-muted)" />
          </marker>
        </defs>
      </svg>

      <div className="mt-4 flex flex-wrap gap-4 border-t pt-3 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5" style={{ background: "var(--risk-low)" }} /> Wave 2 depends on Wave 1 foundations</span>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5" style={{ background: "var(--accent)" }} /> Wave 3 depends on Wave 2 shared libraries</span>
        <span className="ml-auto flex items-center gap-1.5"><span className="h-2.5 border-l-2" style={{ borderColor: "var(--risk-critical)" }} /> Q-Day deadline</span>
      </div>
    </div>
  );
}
