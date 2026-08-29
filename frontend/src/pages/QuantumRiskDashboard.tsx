import { Activity, Atom, DatabaseZap, ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { intelligenceApi, apiErrorMessage } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

const colors: Record<string, string> = { critical: "#fb7185", high: "#fb923c", medium: "#facc15", low: "#34d399", secure: "#22d3ee", unknown: "#64748b" };

export function QuantumRiskDashboard() {
  const { data, error, loading, reload } = useAsync(intelligenceApi.risk, []);
  if (loading) return <LoadingState label="Calculating quantum risk intelligence" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [
    { label: "Vulnerable assets", value: data.metrics.vulnerable_assets, icon: Atom, color: "text-violet-300", bg: "bg-violet-400/10" },
    { label: "Critical quantum risks", value: data.metrics.critical_quantum_risks, icon: ShieldAlert, color: "text-rose-300", bg: "bg-rose-400/10" },
    { label: "HNDL exposures", value: data.metrics.hndl_exposures, icon: DatabaseZap, color: "text-orange-300", bg: "bg-orange-400/10" },
    { label: "Average risk score", value: data.metrics.average_risk_score, icon: Activity, color: "text-brand-300", bg: "bg-brand-400/10" },
  ];
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Phase 2 intelligence" title="Quantum risk dashboard" description="Prioritize cryptographic exposure using quantum vulnerability, HNDL, blast radius, business impact, migration complexity, and evidence confidence." />
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, icon: Icon, color, bg }) => <Card key={label} className="p-5"><div className="flex items-start justify-between"><div><p className="text-xs text-slate-500">{label}</p><p className="mt-3 text-3xl font-semibold text-white">{value}</p></div><span className={`rounded-xl p-2.5 ${bg} ${color}`}><Icon className="h-5 w-5" /></span></div></Card>)}
      </section>
      <section className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5 md:p-6"><p className="text-sm font-semibold text-white">Algorithm vulnerability</p><p className="mt-1 text-xs text-slate-500">Quantum classification across discovered cryptography</p><div className="mt-5 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.algorithm_vulnerability_distribution}><CartesianGrid vertical={false} stroke="rgba(148,163,184,.08)" /><XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} /><Bar dataKey="value" fill="#a78bfa" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></Card>
        <Card className="p-5 md:p-6"><p className="text-sm font-semibold text-white">Final risk severity</p><p className="mt-1 text-xs text-slate-500">Normalized ECDAT score from six intelligence factors</p><div className="mt-5 h-72"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.severity_distribution} dataKey="value" nameKey="name" innerRadius={68} outerRadius={105} paddingAngle={3} stroke="none">{data.severity_distribution.map((item) => <Cell key={item.name} fill={colors[item.name] ?? "#64748b"} />)}</Pie><Tooltip contentStyle={{ background: "#101e31", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12 }} /></PieChart></ResponsiveContainer></div></Card>
      </section>
      <Card className="overflow-hidden"><div className="border-b border-white/[0.06] px-5 py-4"><p className="text-sm font-semibold text-white">Highest-priority assets</p></div>{data.items.length ? <div className="divide-y divide-white/[0.05]">{data.items.slice(0, 6).map((item) => <div key={item.asset_id} className="grid gap-3 px-5 py-4 md:grid-cols-[1fr_140px_140px_120px] md:items-center"><div><p className="text-sm font-medium text-slate-100">{item.asset_name}</p><p className="mt-1 text-xs text-slate-600">{item.algorithm ?? item.asset_type} · {item.dependent_systems} affected systems</p></div><p className="text-xs text-slate-400">HNDL <span className="capitalize text-orange-300">{item.hndl_risk}</span></p><p className="text-xs text-slate-400">Confidence <span className="text-brand-300">{item.evidence_confidence}%</span></p><div className="flex items-center gap-2"><SeverityBadge severity={item.severity} /><span className="font-mono text-sm text-white">{Math.round(item.final_score)}</span></div></div>)}</div> : <EmptyState title="No intelligence yet" body="Complete a discovery scan to calculate Phase 2 risk." />}</Card>
    </div>
  );
}
