import { Atom, Boxes, Route, ScanLine, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function SecurityOperations() {
  const { data, error, loading, reload } = useAsync(enterpriseApi.overview, []);
  if (loading) return <LoadingState label="Loading security operations" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [["Assets", data.assets, Boxes], ["Critical risks", data.critical_risks, ShieldAlert], ["Scans", data.scans, ScanLine], ["Migration assets", data.migration_assets, Route]] as const;
  return <div className="space-y-8"><PageHeader eyebrow="Security operations" title="Cryptographic operations center" description="Monitor discovery activity, quantum exposure, and migration readiness for your organization." /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, Icon]) => <Card key={label} className="p-5"><Icon className="h-5 w-5 text-brand-300" /><p className="mt-5 text-xs text-slate-500">{label}</p><p className="mt-1 text-3xl font-bold text-white">{value}</p></Card>)}</div><Card className="p-6"><div className="flex items-center gap-3"><Atom className="h-5 w-5 text-brand-300" /><p className="font-semibold text-white">Priority workflows</p></div><div className="mt-5 grid gap-3 md:grid-cols-3"><Link className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-sm text-slate-300 hover:border-brand-300/30" to="/quantum-risk">Review quantum risks</Link><Link className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-sm text-slate-300 hover:border-brand-300/30" to="/upload">Run discovery scan</Link><Link className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-sm text-slate-300 hover:border-brand-300/30" to="/migration">Track migration waves</Link></div></Card></div>;
}
