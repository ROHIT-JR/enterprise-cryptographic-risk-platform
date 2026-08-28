import { ChevronLeft, ChevronRight, ExternalLink, FileSearch, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { apiErrorMessage, assetsApi } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SeverityBadge } from "../components/ui";
import type { Asset, Severity } from "../types/api";

export function AssetExplorer() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [assetType, setAssetType] = useState("");
  const [severity, setSeverity] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Awaited<ReturnType<typeof assetsApi.list>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState<Asset | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => { setDebouncedSearch(search); setPage(1); }, 280);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(null);
    assetsApi.list({ search: debouncedSearch || undefined, asset_type: assetType || undefined, severity: severity || undefined, page, page_size: 20 })
      .then((result) => { if (current) setData(result); })
      .catch((caught) => { if (current) setError(caught); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [debouncedSearch, assetType, severity, page]);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Cryptographic inventory" title="Asset explorer" description="Search normalized evidence across applications, libraries, algorithms, protocols, certificates, and configurations." />
      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_200px_180px]">
          <label className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" /><input value={search} onChange={(event) => setSearch(event.target.value)} className="field pl-10" placeholder="Search asset, algorithm, evidence, or location" /></label>
          <select value={assetType} onChange={(event) => { setAssetType(event.target.value); setPage(1); }} className="field"><option value="">All asset types</option><option value="application">Application</option><option value="library">Library</option><option value="algorithm">Algorithm</option><option value="certificate">Certificate</option><option value="protocol">Protocol</option><option value="configuration">Configuration</option></select>
          <select value={severity} onChange={(event) => { setSeverity(event.target.value); setPage(1); }} className="field"><option value="">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
        </div>
      </Card>

      {loading ? <LoadingState label="Loading asset inventory" /> : error ? <ErrorState message={apiErrorMessage(error)} /> : data ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-left">
              <thead className="border-b border-white/[0.06] bg-black/10 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600"><tr><th className="px-5 py-4">Asset</th><th className="px-4 py-4">Type</th><th className="px-4 py-4">Algorithm</th><th className="px-4 py-4">Location & evidence</th><th className="px-4 py-4">Risk</th><th className="px-5 py-4" /></tr></thead>
              <tbody className="divide-y divide-white/[0.05]">
                {data.items.map((asset) => (
                  <tr key={asset.id} onClick={() => setSelected(asset)} className="cursor-pointer text-sm transition hover:bg-white/[0.025]">
                    <td className="px-5 py-4"><p className="font-medium text-slate-100">{asset.name}</p><p className="mt-1 text-xs text-slate-600">{asset.project_name}</p></td>
                    <td className="px-4 py-4"><span className="rounded-md bg-white/[0.05] px-2 py-1 text-[11px] capitalize text-slate-400">{asset.type}</span></td>
                    <td className="px-4 py-4 font-mono text-xs text-brand-200">{asset.algorithm ?? "—"}</td>
                    <td className="max-w-md px-4 py-4"><p className="truncate font-mono text-[11px] text-slate-400">{asset.location}</p><p className="mt-1 truncate text-xs text-slate-600">{asset.evidence}</p></td>
                    <td className="px-4 py-4">{asset.risk ? <div className="flex items-center gap-2"><SeverityBadge severity={asset.risk.severity} /><span className="font-mono text-xs text-slate-400">{Math.round(asset.risk.score)}</span></div> : "—"}</td>
                    <td className="px-5 py-4 text-right"><ExternalLink className="ml-auto h-4 w-4 text-slate-600" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.items.length && <EmptyState title="No matching assets" body="Adjust the filters or start a new discovery scan." />}
          <div className="flex items-center justify-between border-t border-white/[0.06] px-5 py-4 text-xs text-slate-500">
            <span>{data.total ? `${(page - 1) * data.page_size + 1}–${Math.min(page * data.page_size, data.total)} of ${data.total}` : "0 assets"}</span>
            <div className="flex gap-2"><button disabled={page === 1} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-white/10 p-2 hover:bg-white/5 disabled:opacity-30"><ChevronLeft className="h-4 w-4" /></button><button disabled={page * data.page_size >= data.total} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-white/10 p-2 hover:bg-white/5 disabled:opacity-30"><ChevronRight className="h-4 w-4" /></button></div>
          </div>
        </Card>
      ) : null}

      {selected && <AssetDrawer asset={selected} close={() => setSelected(null)} />}
    </div>
  );
}

function AssetDrawer({ asset, close }: { asset: Asset; close: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 bg-black/65 backdrop-blur-sm" onClick={close} aria-label="Close asset details" />
      <aside className="relative h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-ink-900 p-6 shadow-2xl md:p-8">
        <button onClick={close} className="absolute right-5 top-5 rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-white"><X className="h-5 w-5" /></button>
        <span className="inline-flex rounded-xl bg-brand-400/10 p-3 text-brand-300"><FileSearch className="h-5 w-5" /></span>
        <p className="mt-6 text-[10px] font-bold uppercase tracking-[0.2em] text-brand-300">{asset.type}</p><h2 className="mt-2 pr-10 text-2xl font-semibold text-white">{asset.name}</h2><p className="mt-2 text-sm text-slate-500">{asset.project_name}</p>
        {asset.risk && <div className="mt-6 flex items-center justify-between rounded-xl border border-white/[0.07] bg-black/15 p-4"><div><p className="text-xs text-slate-500">Risk score</p><p className="mt-1 text-2xl font-semibold text-white">{Math.round(asset.risk.score)}<span className="text-sm text-slate-600"> / 100</span></p></div><SeverityBadge severity={asset.risk.severity} /></div>}
        <dl className="mt-8 space-y-5 text-sm"><Detail label="Algorithm" value={asset.algorithm ?? "Not specified"} /><Detail label="Version" value={asset.version ?? "Not reported"} /><Detail label="Location" value={asset.location} mono /><Detail label="Evidence" value={asset.evidence} /><Detail label="Confidence" value={`${Math.round(asset.confidence * 100)}%`} /><Detail label="Dependent assets" value={String(asset.dependency_count)} /></dl>
        {asset.risk && <div className="mt-8"><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Why this score</p><ul className="mt-3 space-y-2">{asset.risk.reasons.map((reason) => <li key={reason} className="flex gap-3 rounded-lg bg-white/[0.025] p-3 text-sm text-slate-300"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />{reason}</li>)}</ul></div>}
      </aside>
    </div>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return <div><dt className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-600">{label}</dt><dd className={`break-words leading-6 text-slate-300 ${mono ? "font-mono text-xs" : ""}`}>{value}</dd></div>;
}

