import { CheckCircle2, Circle, Download, Landmark, MapPin } from "lucide-react";
import { useState } from "react";
import { apiErrorMessage, complianceApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";
import { ReportGenerator } from "../components/ReportGenerator";
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { NQMPhase } from "../types/api";

const STATUS_STYLE: Record<NQMPhase["status"], string> = {
  complete: "border-emerald-300 bg-emerald-50 text-emerald-800",
  "in-progress": "border-amber-300 bg-amber-50 text-amber-800",
  "not-started": "border-zinc-200 bg-zinc-50 text-zinc-500",
};

const STATUS_LABEL: Record<NQMPhase["status"], string> = {
  complete: "Complete",
  "in-progress": "In progress",
  "not-started": "Not started",
};

function PhaseCard({ phase, isCurrent }: { phase: NQMPhase; isCurrent: boolean }) {
  return (
    <Card className={`p-4 ${isCurrent ? "border-indigo-300 ring-1 ring-indigo-200" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">
            Phase {phase.id} · {phase.years}
          </p>
          <h3 className="mt-1 text-sm font-bold text-zinc-950">{phase.name}</h3>
        </div>
        <span
          className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wider ${STATUS_STYLE[phase.status]}`}
        >
          {STATUS_LABEL[phase.status]}
        </span>
      </div>
      <p className="mt-2 text-xs leading-normal text-zinc-500">{phase.description}</p>

      <div className="mt-3">
        <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
          <span>PROGRESS</span>
          <span className="font-semibold text-zinc-800">{phase.progress}%</span>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
          <div
            className={`h-full rounded-full ${phase.status === "complete" ? "bg-emerald-500" : "bg-indigo-600"}`}
            style={{ width: `${phase.progress}%` }}
          />
        </div>
      </div>

      <ul className="mt-3 space-y-2 border-t border-zinc-100 pt-3">
        {phase.requirements.map((req) => (
          <li key={req.id} className="flex items-start gap-2 text-xs">
            {req.complete ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
            ) : (
              <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-300" />
            )}
            <div className="min-w-0">
              <p className={`font-medium ${req.complete ? "text-zinc-800" : "text-zinc-600"}`}>{req.label}</p>
              <p className="mt-0.5 text-[11px] text-zinc-500">
                {req.evidence} · {req.progress}%
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function ComplianceDashboard() {
  const { user } = useAuth();
  const canExport = user != null && hasPermission(user.role, "export_findings");
  const { data, error, loading, reload } = useAsync(complianceApi.nqm, []);
  const [reportOpen, setReportOpen] = useState(false);

  if (loading) return <LoadingState label="Mapping NQM compliance posture" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="India National Quantum Mission"
        title="NQM Compliance Dashboard"
        description="Phase-by-phase alignment with India's National Quantum Mission and the DST post-quantum migration roadmap."
        action={
          canExport ? (
            <button type="button" className="btn-primary" onClick={() => setReportOpen(true)}>
              <Download className="h-3.5 w-3.5" /> Export Compliance Report
            </button>
          ) : undefined
        }
      />

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Overall NQM progress</p>
            <p className="tabular-nums mt-1 text-2xl font-bold text-zinc-950">{data.overall_progress}%</p>
          </div>
          <p className="max-w-md text-xs text-zinc-500">{data.source}</p>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-zinc-100">
          <div className="h-full rounded-full bg-indigo-600" style={{ width: `${data.overall_progress}%` }} />
        </div>
      </Card>

      <section className="grid gap-4 lg:grid-cols-3">
        {data.phases.map((phase) => (
          <PhaseCard key={phase.id} phase={phase} isCurrent={phase.id === data.current_phase} />
        ))}
      </section>

      <Card className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-zinc-200 bg-zinc-50 text-indigo-600">
            <Landmark className="h-4 w-4" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Sector profile</p>
            <h3 className="mt-0.5 text-sm font-bold text-zinc-950">{data.sector.name}</h3>
            <p className="mt-1 text-xs text-zinc-500">{data.sector.regulator}</p>
          </div>
        </div>
        <p className="mt-3 text-xs leading-normal text-zinc-600">{data.sector.guidance}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded border border-zinc-100 bg-zinc-50 p-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Priority assets</p>
            <ul className="mt-1.5 space-y-1 text-xs text-zinc-700">
              {data.sector.priority_assets.map((item) => (
                <li key={item} className="flex items-start gap-1.5">
                  <MapPin className="mt-0.5 h-3 w-3 shrink-0 text-zinc-400" /> {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded border border-zinc-100 bg-zinc-50 p-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Recommended baseline</p>
            <p className="mt-1.5 text-xs text-zinc-700">{data.sector.recommended_baseline}</p>
          </div>
        </div>
      </Card>

      <ReportGenerator open={reportOpen} onClose={() => setReportOpen(false)} initialKey="nqm-compliance" />
    </div>
  );
}
