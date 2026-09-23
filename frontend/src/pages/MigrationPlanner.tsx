import { ArrowDown, ChevronDown, ChevronUp, Clock, Route, ShieldCheck, Sparkles, Users, Zap } from "lucide-react";
import { useMemo, useState } from "react";
import { migrationApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { NumberTicker } from "../components/NumberTicker";
import { GanttChart, computeWaveSchedule } from "../components/migration/GanttChart";
import { CostOfDelay } from "../components/migration/CostOfDelay";
import { TaskDetail } from "../components/migration/TaskDetail";
import { useAsync } from "../hooks/useAsync";
import type { MigrationRecommendation, Severity } from "../types/api";

const CURRENT_YEAR = new Date().getFullYear();
// Same "Moderate" scenario baseline used on the Quantum Risk Dashboard
// (config/quantum_timeline.json), kept consistent across Phase 2 pages.
const QDAY_YEAR = 2035;

// Assumed engineer headcount for the schedule shown here — see
// components/migration/GanttChart.tsx for the throughput this implies.
const TEAM_SIZE = 2;

function complexityToSeverity(c: string): Severity {
  if (c === "critical") return "critical";
  if (c === "high") return "high";
  if (c === "medium") return "medium";
  return "low";
}

export function MigrationPlanner() {
  const { data, error, loading, reload } = useAsync(migrationApi.roadmap, []);
  const [selectedWave, setSelectedWave] = useState<number | null>(null);
  const [expandedWave, setExpandedWave] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<{ item: MigrationRecommendation; waveTitle: string } | null>(null);

  const schedule = useMemo(() => (data ? computeWaveSchedule(data.waves) : []), [data]);
  const totalHours = useMemo(() => (data ? data.waves.flatMap((w) => w.items).reduce((sum, i) => sum + i.estimated_hours, 0) : 0), [data]);
  const durationMonths = schedule.at(-1)?.endMonth ?? 0;
  const qDayMonth = Math.max(1, (QDAY_YEAR - CURRENT_YEAR) * 12);
  const baseCompletionYear = CURRENT_YEAR + Math.ceil(durationMonths / 12);

  const wave1QuickWins = useMemo(() => {
    if (!data) return null;
    const wave1 = data.waves.find((w) => w.wave === 1);
    if (!wave1 || wave1.items.length === 0) return null;
    const cheapest = [...wave1.items].sort((a, b) => a.estimated_hours - b.estimated_hours).slice(0, 3);
    const hours = cheapest.reduce((sum, i) => sum + i.estimated_hours, 0);
    return { count: cheapest.length, hours, assets: cheapest.map((i) => i.asset_name) };
  }, [data]);

  if (loading) return <LoadingState label="Building dependency-aware migration waves" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  return (
    <div className="page-enter space-y-8">
      <PageHeader
        eyebrow="Crypto-agility roadmap"
        title="Migration planner"
        description="Migrate trust anchors and shared security components before the applications that depend on them."
      />

      {/* Resource & Effort Summary */}
      <section className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="card-hover p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Total estimated effort</p>
              <p className="tabular-nums mt-2 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
                <NumberTicker end={totalHours} duration={1.1} suffix="h" />
              </p>
            </div>
            <span className="rounded-lg p-2.5" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Clock className="h-5 w-5" /></span>
          </div>
        </Card>
        <Card className="card-hover p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Recommended team size</p>
              <p className="tabular-nums mt-2 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
                <NumberTicker end={TEAM_SIZE} duration={0.8} suffix=" engineers" />
              </p>
            </div>
            <span className="rounded-lg p-2.5" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Users className="h-5 w-5" /></span>
          </div>
        </Card>
        <Card className="card-hover p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Estimated duration</p>
              <p className="tabular-nums mt-2 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
                <NumberTicker end={durationMonths} duration={1.1} suffix=" months" />
              </p>
            </div>
            <span className="rounded-lg p-2.5" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Route className="h-5 w-5" /></span>
          </div>
        </Card>
        <Card className="p-5" style={{ borderColor: "var(--risk-low)" }}>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" style={{ color: "var(--risk-low)" }} />
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--risk-low)" }}>Wave 1 quick win</p>
          </div>
          {wave1QuickWins ? (
            <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              Migrate <strong style={{ color: "var(--text-primary)" }}>{wave1QuickWins.count} assets</strong> ({wave1QuickWins.assets.join(", ")}) —{" "}
              <strong style={{ color: "var(--text-primary)" }}>{wave1QuickWins.hours}h</strong>, unblocks all of Wave 2.
            </p>
          ) : (
            <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>No Wave 1 assets identified yet.</p>
          )}
        </Card>
      </section>

      {/* Gantt chart */}
      <Card className="p-5 md:p-6">
        <p className="mb-1 text-base font-semibold" style={{ color: "var(--text-primary)" }}>Migration Timeline</p>
        <p className="mb-5 text-xs" style={{ color: "var(--text-muted)" }}>
          3-wave dependency-aware roadmap, scheduled from real per-asset effort estimates at a {TEAM_SIZE}-engineer team capacity · click a wave to inspect tasks
        </p>
        <GanttChart schedule={schedule} qDayMonth={qDayMonth} selectedWave={selectedWave} onSelectWave={setSelectedWave} />
      </Card>

      {/* Cost of Delay */}
      <Card className="p-5 md:p-6">
        <p className="mb-1 text-base font-semibold" style={{ color: "var(--text-primary)" }}>Cost of Delay</p>
        <p className="mb-4 text-xs" style={{ color: "var(--text-muted)" }}>What waiting to start actually costs, in quantum exposure time</p>
        <CostOfDelay currentYear={CURRENT_YEAR} baseCompletionYear={baseCompletionYear} qDayYear={QDAY_YEAR} />
      </Card>

      {/* Selected task detail */}
      {selectedTask && (
        <div className="page-enter">
          <TaskDetail item={selectedTask.item} waveTitle={selectedTask.waveTitle} onClose={() => setSelectedTask(null)} />
        </div>
      )}

      {/* Wave cards */}
      {data.waves.length ? (
        <div className="space-y-4">
          {data.waves.map((wave, index) => {
            const isExpanded = expandedWave === wave.wave;
            const waveHours = wave.items.reduce((sum, i) => sum + i.estimated_hours, 0);
            const sched = schedule.find((s) => s.wave === wave.wave);
            return (
              <div key={wave.wave}>
                <Card className="overflow-hidden">
                  <button
                    className="interactive flex w-full flex-col gap-3 border-b px-5 py-4 text-left hover:bg-[var(--bg-hover)] md:flex-row md:items-center"
                    style={{ borderColor: "var(--border)" }}
                    onClick={() => setExpandedWave(isExpanded ? null : wave.wave)}
                  >
                    <span
                      className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-sm font-bold"
                      style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
                    >
                      {wave.wave}
                    </span>
                    <div className="flex-1">
                      <p className="font-semibold" style={{ color: "var(--text-primary)" }}>Wave {wave.wave}: {wave.title}</p>
                      <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{wave.reason}</p>
                    </div>
                    <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
                      <span>{wave.items.length} assets</span>
                      <span>~{waveHours}h</span>
                      <span>Months {sched ? sched.startMonth + 1 : "?"}–{sched?.endMonth}</span>
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="page-enter divide-y" style={{ borderColor: "var(--border)" }}>
                      {wave.items.slice(0, 16).map((item) => (
                        <button
                          key={item.asset_id}
                          onClick={() => setSelectedTask({ item, waveTitle: `Wave ${wave.wave}: ${wave.title}` })}
                          className="interactive grid w-full gap-3 px-5 py-3.5 text-left text-sm hover:bg-[var(--bg-hover)] md:grid-cols-[1fr_180px_1fr_110px] md:items-center"
                          style={{ borderColor: "var(--border)" }}
                        >
                          <div>
                            <p className="font-medium" style={{ color: "var(--text-primary)" }}>{item.asset_name}</p>
                            <p className="mt-0.5 text-xs capitalize" style={{ color: "var(--text-muted)" }}>{item.asset_type}</p>
                          </div>
                          <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{item.current_algorithm}</p>
                          <div className="flex items-center gap-2 text-xs font-medium" style={{ color: "var(--accent)" }}>
                            <ShieldCheck className="h-4 w-4" />{item.recommended_algorithm}
                          </div>
                          <SeverityBadge severity={complexityToSeverity(item.complexity)} />
                        </button>
                      ))}
                    </div>
                  )}
                </Card>
                {index < data.waves.length - 1 && (
                  <div className="my-2 flex items-center justify-center gap-1.5">
                    <ArrowDown className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
                    <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>Wave {wave.wave + 1} sequencing follows</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <Card><EmptyState title="No migration roadmap" body="Quantum-vulnerable assets will appear here after intelligence analysis." /></Card>
      )}

      <div
        className="flex items-center gap-3 rounded-xl border px-4 py-3 text-sm"
        style={{ borderColor: "var(--accent)", background: "var(--accent-soft)", color: "var(--accent)" }}
      >
        <Sparkles className="h-5 w-5 shrink-0" />
        {data.total_assets} assets have been sequenced using dependency-aware ordering across {data.waves.length} migration waves.
      </div>
    </div>
  );
}
