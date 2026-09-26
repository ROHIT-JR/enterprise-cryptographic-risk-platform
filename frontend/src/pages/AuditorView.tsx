import { Download, FileCheck2, History } from "lucide-react";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { relativeTime } from "../utils/format";

export function AuditorView() {
  const { data, error, loading, reload } = useAsync(enterpriseApi.audit, []);
  if (loading) return <PageSkeleton rows={4} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  async function download(type: "inventory" | "quantum-risk" | "migration", format: "json" | "pdf") {
    const blob = await enterpriseApi.report(type, format);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `ecdat-${type}.${format}`; anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Assurance and compliance"
        title="Auditor view"
        description="Export evidence packages and inspect the organization-scoped immutable activity trail."
      />
      <Card className="card-hover p-5">
        <div className="flex items-center gap-2.5">
          <FileCheck2 className="h-5 w-5 text-indigo-600" strokeWidth={1.75} />
          <p className="text-sm font-bold text-zinc-950">Enterprise reports</p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {(["inventory", "quantum-risk", "migration"] as const).map((type) => (
            <div key={type} className="rounded border border-zinc-200 bg-zinc-50 p-4">
              <p className="font-mono text-xs font-bold uppercase tracking-wider text-zinc-900">
                {type.replace("-", " ")}
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => void download(type, "json")}
                  className="flex items-center gap-1.5 rounded border border-zinc-200 bg-white px-3 py-1.5 font-mono text-xs font-semibold text-zinc-700 shadow-xs hover:bg-zinc-50 hover:text-zinc-900"
                >
                  <Download className="h-3 w-3 text-zinc-500" />
                  JSON
                </button>
                <button
                  onClick={() => void download(type, "pdf")}
                  className="flex items-center gap-1.5 rounded border border-indigo-200 bg-indigo-50 px-3 py-1.5 font-mono text-xs font-semibold text-indigo-700 shadow-xs hover:bg-indigo-100"
                >
                  <Download className="h-3 w-3 text-indigo-600" />
                  PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card className="card-hover p-5">
        <div className="flex items-center gap-2.5">
          <History className="h-5 w-5 text-indigo-600" strokeWidth={1.75} />
          <p className="text-sm font-bold text-zinc-950">Audit history</p>
        </div>
        <div className="mt-4 divide-y divide-zinc-100">
          {data.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div>
                <p className="font-semibold text-zinc-900">{item.action.replaceAll(".", " ")}</p>
                <p className="mt-0.5 font-mono text-[10px] text-zinc-500">{item.user_id ?? "system"}</p>
              </div>
              <span className="font-mono text-xs text-zinc-500">{relativeTime(item.timestamp)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
