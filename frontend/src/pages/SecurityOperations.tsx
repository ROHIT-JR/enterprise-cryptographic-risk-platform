import { Atom, Boxes, Route, ScanLine, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function SecurityOperations() {
  const { data, error, loading, reload } = useAsync(enterpriseApi.overview, []);
  if (loading) return <PageSkeleton rows={1} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [
    ["Assets", data.assets, Boxes],
    ["Critical risks", data.critical_risks, ShieldAlert],
    ["Scans", data.scans, ScanLine],
    ["Migration assets", data.migration_assets, Route],
  ] as const;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Security operations"
        title="Cryptographic operations center"
        description="Monitor discovery activity, quantum exposure, and migration readiness for your organization."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, Icon]) => (
          <Card key={label} className="card-hover p-5">
            <Icon className="h-5 w-5" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
            <p className="mt-4 font-mono text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>{value}</p>
          </Card>
        ))}
      </div>
      <Card className="p-6">
        <div className="flex items-center gap-3">
          <Atom className="h-5 w-5" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Priority workflows</p>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <Link
            className="interactive flex items-center justify-between rounded-lg border p-4 text-sm font-semibold"
            style={{ borderColor: "var(--border)", background: "var(--bg-hover)", color: "var(--text-secondary)" }}
            to="/quantum-risk"
          >
            <span>Review quantum risks</span>
            <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>→</span>
          </Link>
          <Link
            className="interactive flex items-center justify-between rounded-lg border p-4 text-sm font-semibold"
            style={{ borderColor: "var(--border)", background: "var(--bg-hover)", color: "var(--text-secondary)" }}
            to="/upload"
          >
            <span>Run discovery scan</span>
            <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>→</span>
          </Link>
          <Link
            className="interactive flex items-center justify-between rounded-lg border p-4 text-sm font-semibold"
            style={{ borderColor: "var(--border)", background: "var(--bg-hover)", color: "var(--text-secondary)" }}
            to="/migration"
          >
            <span>Track migration waves</span>
            <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>→</span>
          </Link>
        </div>
      </Card>
    </div>
  );
}
