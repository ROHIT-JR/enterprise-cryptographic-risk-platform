import { ArrowDown, ChevronDown, ChevronUp, Route, ShieldCheck, Info } from "lucide-react";
import { useState } from "react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { MigrationRecommendation, Severity } from "../types/api";

// Wave configuration — months + colors
const WAVE_CONFIG = [
  { wave: 1, start: 0,  end: 6,  color: "#06b6d4", bg: "rgba(6,182,212,0.15)",  border: "rgba(6,182,212,0.35)",  label: "Foundations" },
  { wave: 2, start: 3,  end: 12, color: "#8b5cf6", bg: "rgba(139,92,246,0.15)", border: "rgba(139,92,246,0.35)", label: "Libraries" },
  { wave: 3, start: 9,  end: 18, color: "#f59e0b", bg: "rgba(245,158,11,0.15)", border: "rgba(245,158,11,0.35)", label: "Applications" },
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
      <p className="mb-1 text-sm font-semibold text-white">Migration Timeline</p>
      <p className="mb-5 text-xs text-slate-500">3-wave dependency-aware migration roadmap · click a wave to see task details</p>

      {/* Month axis */}
      <div className="mb-2 flex pl-28">
        {Array.from({ length: TOTAL_MONTHS }, (_, i) => i + 1).map((m) => (
          <div key={m} className="flex-1 text-center text-[9px] text-slate-700">{m}</div>
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
                className="w-28 shrink-0 text-left"
                onClick={() => onSelectWave(isSelected ? null : wave)}
              >
                <p className="text-[11px] font-bold" style={{ color }}>Wave {wave}</p>
                <p className="text-[10px] text-slate-500">{label}</p>
              </button>
              {/* Track */}
              <div className="relative h-8 flex-1 rounded-lg bg-ink-850">
                {/* Month grid lines */}
                {Array.from({ length: TOTAL_MONTHS - 1 }, (_, i) => i + 1).map((m) => (
                  <div
                    key={m}
                    className="absolute inset-y-0 w-px bg-white/[0.03]"
                    style={{ left: `${(m / TOTAL_MONTHS) * 100}%` }}
                  />
                ))}
                {/* Bar */}
                <button
                  className="absolute inset-y-1 rounded-lg transition hover:brightness-110"
                  style={{
                    left: `${barLeft}%`,
                    width: `${barWidth}%`,
                    background: bg,
                    border: `1px solid ${border}`,
                    boxShadow: isSelected ? `0 0 20px ${color}40` : "none",
                  }}
                  onClick={() => onSelectWave(isSelected ? null : wave)}
                >
                  <span className="flex h-full items-center justify-center text-[10px] font-bold" style={{ color }}>
                    Months {start + 1}–{end}
                  </span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Month ruler */}
      <div className="mt-3 pl-28">
        <div className="relative h-1 w-full rounded-full bg-ink-750">
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-brand-500/40 via-violet-500/40 to-amber-500/40" />
        </div>
        <div className="mt-1 flex justify-between text-[9px] text-slate-700">
          <span>Month 1</span><span>Month 6</span><span>Month 12</span><span>Month 18</span>
        </div>
      </div>

      {/* Dependency arrows legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-[10px] text-slate-600">
        <span className="flex items-center gap-1"><span className="h-px w-6 bg-brand-400/40 border-t border-dashed border-brand-400/40" /> Wave 2 depends on Wave 1</span>
        <span className="flex items-center gap-1"><span className="h-px w-6 border-t border-dashed border-violet-400/40" /> Wave 3 depends on Wave 2</span>
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
    <Card className="overflow-hidden animate-fade-in">
      <div
        className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4"
        style={{ borderTopWidth: 2, borderTopColor: cfg?.color }}
      >
        <span
          className="grid h-9 w-9 place-items-center rounded-xl text-sm font-extrabold"
          style={{ background: cfg?.bg, color: cfg?.color }}
        >
          {waveNum}
        </span>
        <div>
          <p className="font-semibold text-white">Wave {waveNum}: {cfg?.label}</p>
          <p className="text-xs text-slate-500">
            {items.length} assets · est. {totalEffort}h total effort · Months {cfg?.start !== undefined ? cfg.start + 1 : "?"}–{cfg?.end}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <Info className="h-4 w-4 text-brand-300" />
          {waveNum === 2 ? "Depends on Wave 1" : waveNum === 3 ? "Depends on Wave 2" : "Foundation — no dependencies"}
        </div>
      </div>
      <div className="divide-y divide-white/[0.05]">
        {items.slice(0, 12).map((item) => (
          <div key={item.asset_id} className="grid gap-3 px-5 py-4 text-sm md:grid-cols-[1fr_160px_1fr_110px_90px] md:items-center">
            <div>
              <p className="font-medium text-slate-200">{item.asset_name}</p>
              <p className="mt-1 text-xs capitalize text-slate-600">{item.asset_type}</p>
            </div>
            <p className="font-mono text-xs text-slate-500">{item.current_algorithm}</p>
            <div className="flex items-center gap-2 text-xs text-brand-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              {item.recommended_algorithm}
            </div>
            <SeverityBadge severity={complexityToSeverity(item.complexity)} />
            <p className="text-xs text-slate-500">{EFFORT_HOURS[item.complexity] ?? 20}h est.</p>
          </div>
        ))}
        {items.length > 12 && (
          <div className="px-5 py-3 text-center text-xs text-slate-600">
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
        <div className="space-y-5">
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
                    className="flex w-full flex-col gap-3 border-b border-white/[0.06] px-5 py-5 text-left transition hover:bg-white/[0.02] md:flex-row md:items-center"
                    style={{ borderLeftWidth: 3, borderLeftColor: cfg?.color }}
                    onClick={() => setExpandedWave(isExpanded ? null : wave.wave)}
                  >
                    <span
                      className="grid h-11 w-11 shrink-0 place-items-center rounded-xl font-bold"
                      style={{ background: cfg?.bg, color: cfg?.color }}
                    >
                      {wave.wave}
                    </span>
                    <div className="flex-1">
                      <p className="font-semibold text-white">Wave {wave.wave}: {wave.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{wave.reason}</p>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-600">
                      <span>{wave.items.length} assets</span>
                      <span>~{totalEffort}h</span>
                      <span>Months {cfg?.start !== undefined ? cfg.start + 1 : "?"}–{cfg?.end}</span>
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="divide-y divide-white/[0.05] animate-fade-in">
                      {wave.items.slice(0, 16).map((item) => (
                        <div key={item.asset_id} className="grid gap-3 px-5 py-4 text-sm md:grid-cols-[1fr_180px_1fr_110px] md:items-center">
                          <div>
                            <p className="font-medium text-slate-200">{item.asset_name}</p>
                            <p className="mt-1 text-xs capitalize text-slate-600">{item.asset_type}</p>
                          </div>
                          <p className="font-mono text-xs text-slate-500">{item.current_algorithm}</p>
                          <div className="flex items-center gap-2 text-xs text-brand-200">
                            <ShieldCheck className="h-4 w-4" />{item.recommended_algorithm}
                          </div>
                          <SeverityBadge severity={complexityToSeverity(item.complexity)} />
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
                {index < data.waves.length - 1 && (
                  <div className="my-2 flex items-center justify-center gap-2">
                    <ArrowDown className="h-4 w-4 text-slate-700" />
                    <span className="text-[10px] text-slate-700">Wave {wave.wave + 1} depends on this wave completing</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <Card><EmptyState title="No migration roadmap" body="Quantum-vulnerable assets will appear here after intelligence analysis." /></Card>
      )}

      <div className="flex items-center gap-3 rounded-xl border border-brand-300/15 bg-brand-400/[0.05] px-4 py-3 text-sm text-brand-100">
        <Route className="h-5 w-5 text-brand-300" />
        {data.total_assets} assets have been sequenced using dependency-aware ordering across {data.waves.length} migration waves.
      </div>
    </div>
  );
}
