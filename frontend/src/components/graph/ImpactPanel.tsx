import { ArrowRight, FileText, Network, X } from "lucide-react";
import { Card, SeverityBadge } from "../ui";
import type { BlastRadiusImpactSummary, GraphNode, Severity } from "../../types/api";

const DEGREE_LABELS: Record<string, string> = {
  "1": "Direct (1°) systems",
  "2": "Secondary (2°) risk",
  "3": "Tertiary (3°) risk",
};

function degreeColor(level: string): string {
  if (level === "1") return "var(--risk-critical)";
  if (level === "2") return "var(--risk-high)";
  return "var(--risk-medium)";
}

export function ImpactPanel({
  assetName,
  impactSummary,
  directNodes,
  onClose,
  onViewMigrationPlan,
  onGenerateReport,
}: {
  assetName: string;
  impactSummary: BlastRadiusImpactSummary;
  directNodes: GraphNode[];
  onClose: () => void;
  onViewMigrationPlan: () => void;
  onGenerateReport: () => void;
}) {
  const degreeEntries = Object.entries(impactSummary.by_degree).sort(([a], [b]) => Number(a) - Number(b));
  // Share of the affected systems that are themselves critical/high-criticality
  // (not "% of infrastructure" — we don't have a total-systems-in-org figure
  // to divide by, so this is the honest ratio the backend's real data supports).
  const criticalSharePercent = impactSummary.total_affected > 0
    ? Math.round((impactSummary.critical_systems / impactSummary.total_affected) * 100)
    : 0;
  const effortWeeks = Math.max(1, Math.round(impactSummary.estimated_effort_hours / 40));
  const effortMonths = Math.max(1, Math.round(impactSummary.estimated_effort_hours / 160));

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b px-5 py-3.5" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4" style={{ color: "var(--risk-critical)" }} />
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Blast Radius Impact</p>
        </div>
        <button onClick={onClose} className="interactive rounded p-1 hover:bg-[var(--bg-hover)]" style={{ color: "var(--text-muted)" }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="px-5 py-4">
        <p className="font-mono text-[10px] uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Compromised</p>
        <p className="mt-0.5 text-sm font-bold" style={{ color: "var(--text-primary)" }}>{assetName}</p>
      </div>

      <div className="divide-y px-5" style={{ borderColor: "var(--border)" }}>
        {degreeEntries.map(([level, count]) => (
          <div key={level} className="flex items-center justify-between py-3 text-sm" style={{ borderColor: "var(--border)" }}>
            <span style={{ color: "var(--text-secondary)" }}>{DEGREE_LABELS[level] ?? `Degree ${level}`}</span>
            <span className="tabular-nums font-bold" style={{ color: degreeColor(level) }}>{count}</span>
          </div>
        ))}
        <div className="flex items-center justify-between py-3 text-sm font-semibold">
          <span style={{ color: "var(--text-primary)" }}>Total blast radius</span>
          <span className="tabular-nums" style={{ color: "var(--risk-critical)" }}>{impactSummary.total_affected} systems</span>
        </div>
      </div>

      <div className="px-5 py-3">
        <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          <span>Critical/high share of affected systems</span>
          <span>{criticalSharePercent}%</span>
        </div>
        <div className="mt-1.5 h-1.5 w-full rounded-full" style={{ background: "var(--bg-hover)" }}>
          <div
            className="h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${criticalSharePercent}%`, background: "var(--risk-critical)" }}
          />
        </div>
      </div>

      {directNodes.length > 0 && (
        <div className="px-5 pb-4">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: "var(--text-muted)" }}>
            Directly affected
          </p>
          <div className="space-y-2">
            {directNodes.slice(0, 6).map((node) => (
              <div
                key={node.id}
                className="flex items-center justify-between rounded-lg border px-3 py-2 text-xs"
                style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}
              >
                <span className="truncate font-medium" style={{ color: "var(--text-secondary)" }}>{node.label}</span>
                <SeverityBadge severity={((node.properties.severity as string) ?? "medium") as Severity} />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="px-5 pb-4">
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: "var(--text-muted)" }}>
          Estimated migration effort
        </p>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          <span className="font-bold" style={{ color: "var(--text-primary)" }}>{impactSummary.estimated_effort_hours} hrs</span>
          {" "}· roughly {effortWeeks} {effortWeeks === 1 ? "week" : "weeks"} ({effortMonths} {effortMonths === 1 ? "month" : "months"}) with one engineer
        </p>
      </div>

      {impactSummary.critical_path.length > 1 && (
        <div className="px-5 pb-4">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: "var(--text-muted)" }}>
            Recommended action
          </p>
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Migrate <strong style={{ color: "var(--text-primary)" }}>{assetName}</strong> first — it sits at the root of the longest
            dependency chain ({impactSummary.critical_path.join(" → ")}), and {impactSummary.critical_systems} of the affected
            systems are critical or high-criticality.
          </p>
        </div>
      )}

      <div className="flex gap-2 border-t px-5 py-4" style={{ borderColor: "var(--border)" }}>
        <button onClick={onViewMigrationPlan} className="interactive btn-primary flex-1 justify-between">
          View Migration Plan <ArrowRight className="h-3.5 w-3.5" />
        </button>
        <button onClick={onGenerateReport} className="interactive btn-secondary" title="Generate Report">
          <FileText className="h-3.5 w-3.5" />
        </button>
      </div>
    </Card>
  );
}
