import { Download, FileCheck2, History } from "lucide-react";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { relativeTime } from "../utils/format";

export function AuditorView() {
  const { data, error, loading, reload } = useAsync(enterpriseApi.audit, []);
  if (loading) return <LoadingState label="Loading audit evidence" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  async function download(type: "inventory" | "quantum-risk" | "migration", format: "json" | "pdf") {
    const blob = await enterpriseApi.report(type, format);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `ecdat-${type}.${format}`; anchor.click();
    URL.revokeObjectURL(url);
  }
  return <div className="space-y-8"><PageHeader eyebrow="Assurance and compliance" title="Auditor view" description="Export evidence packages and inspect the organization-scoped immutable activity trail." /><Card className="p-5"><div className="flex items-center gap-3"><FileCheck2 className="h-5 w-5 text-brand-300" /><p className="font-semibold text-white">Enterprise reports</p></div><div className="mt-5 grid gap-3 md:grid-cols-3">{(["inventory", "quantum-risk", "migration"] as const).map((type) => <div key={type} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"><p className="text-sm capitalize text-slate-200">{type.replace("-", " ")}</p><div className="mt-3 flex gap-2"><button onClick={() => void download(type, "json")} className="flex items-center gap-1 rounded-lg bg-white/5 px-3 py-2 text-xs text-slate-300"><Download className="h-3 w-3" />JSON</button><button onClick={() => void download(type, "pdf")} className="flex items-center gap-1 rounded-lg bg-brand-400/10 px-3 py-2 text-xs text-brand-200"><Download className="h-3 w-3" />PDF</button></div></div>)}</div></Card><Card className="p-5"><div className="flex items-center gap-3"><History className="h-5 w-5 text-brand-300" /><p className="font-semibold text-white">Audit history</p></div><div className="mt-4 divide-y divide-white/[0.05]">{data.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 py-3 text-sm"><div><p className="text-slate-200">{item.action.replaceAll(".", " ")}</p><p className="mt-1 font-mono text-[10px] text-slate-600">{item.user_id ?? "system"}</p></div><span className="text-xs text-slate-500">{relativeTime(item.timestamp)}</span></div>)}</div></Card></div>;
}
