import { ArrowDown, ChevronDown, ChevronUp, Route, ShieldCheck, Info } from "lucide-react";
import { useState } from "react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { MigrationRecommendation, Severity } from "../types/api";

// Wave configuration — months + human light colors
const WAVE_CONFIG = [
  { wave: 1, start: 0,  end: 6,  color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd", label: "Foundations" },
  { wave: 2, start: 3,  end: 12, color: "#4f46e5", bg: "#eef2ff", border: "#c7d2fe", label: "Libraries" },
  { wave: 3, start: 9,  end: 18, color: "#b45309", bg: "#fffbeb", border: "#fde68a", label: "Applications" },
] as const;

const TOTAL_MONTHS = 18;

// Complexity → effort multiplier
const EFFORT_HOURS: Record<string, number> = {
  critical: 80,
  high: 40,
  medium: 20,
  low: 8,
};

function complexityToSeverity(c: string): Severity {
  if (c === "critical") return "critical";
  if (c === "high") return "high";
  if (c === "medium") return "medium";
  return "low";
}

// ─────────────────────────────────────────────
// Gantt Chart
// ─────────────────────────────────────────────
function GanttChart({ selectedWave, onSelectWave }: { selectedWave: number | null; onSelectWave: (w: number | null) => void }) {
  return (
    <Card className="p-5 md:p-6">
      <p className="mb-1 text-base font-semibold text-slate-900">Migration Timeline</p>
      <p className="mb-5 text-xs text-slate-500">3-wave dependency-aware migration roadmap · select a wave below to inspect tasks</p>

      {/* Month axis */}
      <div className="mb-2 flex pl-28">
        {Array.from({ length: TOTAL_MONTHS }, (_, i) => i + 1).map((m) => (
          <div key={m} className="flex-1 text-center text-[10px] font-medium text-slate-400">{m}</div>
        ))}
      </div>

      {/* Bars */}
      <div className="space-y-3">
        {WAVE_CONFIG.map(({ wave, start, end, color, bg, border, label }) => {
          const isSelected = selectedWave === wave;
          const barLeft = (start / TOTAL_MONTHS) * 100;
          const barWidth = ((end - start) / TOTAL_MONTHS) * 100;
          return (
            <div key={wave} className="flex items-center gap-3">
              {/* Label */}
              <button
                className="w-28 shrink-0 text-left transition hover:opacity-80"
                onClick={() => onSelectWave(isSelected ? null : wave)}
              >
                <p className="text-xs font-bold" style={{ color }}>Wave {wave}</p>
                <p className="text-[11px] text-slate-500">{label}</p>
              </button>
              {/* Track */}
              <div className="relative h-9 flex-1 rounded-lg border border-slate-200 bg-slate-50 overflow-hidden">
                {/* Month grid lines */}
                {Array.from({ length: TOTAL_MONTHS - 1 }, (_, i) => i + 1).map((m) => (
                  <div
                    key={m}
                    className="absolute inset-y-0 w-px bg-slate-200/70"
                    style={{ left: `${(m / TOTAL_MONTHS) * 100}%` }}
                  />
                ))}
                {/* Bar */}
                <button
                  className="absolute inset-y-1 rounded-md border transition hover:opacity-95"
                  style={{
                    left: `${barLeft}%`,
                    width: `${barWidth}%`,
                    background: bg,
                    borderColor: border,
                    boxShadow: isSelected ? `0 0 0 2px ${color}` : "none",
                  }}
                  onClick={() => onSelectWave(isSelected ? null : wave)}
                >
                  <span className="flex h-full items-center justify-center text-xs font-semibold" style={{ color }}>
                    Months {start + 1}–{end}
                  </span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Month ruler */}
      <div className="mt-4 pl-28">
        <div className="relative h-1 w-full rounded-full bg-slate-200" />
        <div className="mt-1.5 flex justify-between text-[11px] text-slate-400">
          <span>Month 1</span><span>Month 6</span><span>Month 12</span><span>Month 18</span>
        </div>
      </div>

      {/* Dependency arrows legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500 border-t border-slate-100 pt-3">
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-sky-500" /> Wave 2 depends on Wave 1 foundations</span>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-indigo-500" /> Wave 3 depends on Wave 2 shared libraries</span>
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────
// Wave detail panel
// ─────────────────────────────────────────────
function WaveDetailPanel({
  waveNum,
  items,
}: {
  waveNum: number;
  items: MigrationRecommendation[];
}) {
  const cfg = WAVE_CONFIG.find((w) => w.wave === waveNum);
  const totalEffort = items.reduce(
    (sum, item) => sum + (EFFORT_HOURS[item.complexity] ?? 20),
    0,
  );
  return (
    <Card className="overflow-hidden animate-fade-in border-t-2" style={{ borderTopColor: cfg?.color }}>
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4 bg-slate-50/50">
        <span
          className="grid h-8 w-8 place-items-center rounded-lg text-xs font-bold"
          style={{ background: cfg?.bg, color: cfg?.color, border: `1px solid ${cfg?.border}` }}
        >
          {waveNum}
        </span>
        <div>
          <p className="font-semibold text-slate-900">Wave {waveNum}: {cfg?.label}</p>
          <p className="text-xs text-slate-500">
            {items.length} assets · ~{totalEffort} hours estimated effort · Window: Months {cfg?.start !== undefined ? cfg.start + 1 : "?"}–{cfg?.end}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
          <Info className="h-4 w-4 text-blue-600" />
          {waveNum === 2 ? "Requires Wave 1 completion" : waveNum === 3 ? "Requires Wave 2 completion" : "Foundation layer"}
        </div>
      </div>
      <div className="divide-y divide-slate-100">
        {items.slice(0, 12).map((item) => (
          <div key={item.asset_id} className="grid gap-3 px-5 py-3.5 text-sm transition hover:bg-slate-50 md:grid-cols-[1fr_160px_1fr_110px_90px] md:items-center">
            <div>
              <p className="font-medium text-slate-800">{item.asset_name}</p>
              <p className="mt-0.5 text-xs capitalize text-slate-400">{item.asset_type}</p>
            </div>
            <p className="font-mono text-xs text-slate-500">{item.current_algorithm}</p>
            <div className="flex items-center gap-2 text-xs font-medium text-blue-700">
              <ShieldCheck className="h-4 w-4 shrink-0 text-blue-600" />
              {item.recommended_algorithm}
            </div>
            <SeverityBadge severity={complexityToSeverity(item.complexity)} />
            <p className="text-xs text-slate-500">{EFFORT_HOURS[item.complexity] ?? 20}h est.</p>
          </div>
        ))}
        {items.length > 12 && (
          <div className="px-5 py-3 text-center text-xs text-slate-500 bg-slate-50">
            +{items.length - 12} more assets in this wave
          </div>
        )}
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────
export function MigrationPlanner() {
  const { data, error, loading, reload } = useAsync(migrationApi.roadmap, []);
  const [selectedWave, setSelectedWave] = useState<number | null>(null);
  const [expandedWave, setExpandedWave] = useState<number | null>(null);

  if (loading) return <LoadingState label="Building dependency-aware migration waves" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Crypto-agility roadmap"
        title="Migration planner"
        description="Migrate trust anchors and shared security components before the applications that depend on them."
      />

      {/* Gantt chart */}
      <GanttChart selectedWave={selectedWave} onSelectWave={setSelectedWave} />

      {/* Selected wave detail panel */}
      {selectedWave !== null && (() => {
        const wave = data.waves.find((w) => w.wave === selectedWave);
        if (!wave) return null;
        return <WaveDetailPanel waveNum={selectedWave} items={wave.items} />;
      })()}

      {/* Wave cards */}
      {data.waves.length ? (
        <div className="space-y-4">
          {data.waves.map((wave, index) => {
            const cfg = WAVE_CONFIG.find((w) => w.wave === wave.wave);
            const isExpanded = expandedWave === wave.wave;
            const totalEffort = wave.items.reduce(
              (sum, item) => sum + (EFFORT_HOURS[item.complexity] ?? 20),
              0,
            );
            return (
              <div key={wave.wave}>
                <Card className="overflow-hidden">
                  <button
                    className="flex w-full flex-col gap-3 border-b border-slate-100 px-5 py-4 text-left transition hover:bg-slate-50 md:flex-row md:items-center"
                    style={{ borderLeftWidth: 3, borderLeftColor: cfg?.color }}
                    onClick={() => setExpandedWave(isExpanded ? null : wave.wave)}
                  >
                    <span
                      className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-sm font-bold"
                      style={{ background: cfg?.bg, color: cfg?.color, border: `1px solid ${cfg?.border}` }}
                    >
                      {wave.wave}
                    </span>
                    <div className="flex-1">
                      <p className="font-semibold text-slate-900">Wave {wave.wave}: {wave.title}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{wave.reason}</p>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>{wave.items.length} assets</span>
                      <span>~{totalEffort}h</span>
                      <span>Months {cfg?.start !== undefined ? cfg.start + 1 : "?"}–{cfg?.end}</span>
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="divide-y divide-slate-100 animate-fade-in">
                      {wave.items.slice(0, 16).map((item) => (
                        <div key={item.asset_id} className="grid gap-3 px-5 py-3.5 text-sm transition hover:bg-slate-50 md:grid-cols-[1fr_180px_1fr_110px] md:items-center">
                          <div>
                            <p className="font-medium text-slate-800">{item.asset_name}</p>
                            <p className="mt-0.5 text-xs capitalize text-slate-400">{item.asset_type}</p>
                          </div>
                          <p className="font-mono text-xs text-slate-500">{item.current_algorithm}</p>
                          <div className="flex items-center gap-2 text-xs font-medium text-blue-700">
                            <ShieldCheck className="h-4 w-4 text-blue-600" />{item.recommended_algorithm}
                          </div>
                          <SeverityBadge severity={complexityToSeverity(item.complexity)} />
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
                {index < data.waves.length - 1 && (
                  <div className="my-2 flex items-center justify-center gap-1.5">
                    <ArrowDown className="h-4 w-4 text-slate-400" />
                    <span className="text-[11px] text-slate-400">Wave {wave.wave + 1} sequencing follows</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <Card><EmptyState title="No migration roadmap" body="Quantum-vulnerable assets will appear here after intelligence analysis." /></Card>
      )}

      <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50/60 px-4 py-3 text-sm text-blue-800">
        <Route className="h-5 w-5 text-blue-600 shrink-0" />
        {data.total_assets} assets have been sequenced using dependency-aware ordering across {data.waves.length} migration waves.
      </div>
    </div>
  );
}
