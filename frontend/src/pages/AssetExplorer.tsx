import { ChevronLeft, ChevronRight, ExternalLink, FileSearch, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { apiErrorMessage, assetsApi } from "../api/client";
import { Card, EmptyState, ErrorState, PageHeader, PageSkeleton, SeverityBadge } from "../components/ui";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuFieldTrigger,
  DropdownMenuItem,
} from "../components/DropdownMenu";
import type { Asset, Severity } from "../types/api";

const ASSET_TYPE_OPTIONS = [
  { value: "", label: "All asset types" },
  { value: "application", label: "Application" },
  { value: "library", label: "Library" },
  { value: "algorithm", label: "Algorithm" },
  { value: "certificate", label: "Certificate" },
  { value: "protocol", label: "Protocol" },
  { value: "configuration", label: "Configuration" },
];

const SEVERITY_OPTIONS = [
  { value: "", label: "All severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

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
          <label className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="field pl-10"
              placeholder="Search asset, algorithm, evidence, or location"
            />
          </label>
          <DropdownMenu>
            <DropdownMenuFieldTrigger>
              {ASSET_TYPE_OPTIONS.find((o) => o.value === assetType)?.label ?? "All asset types"}
            </DropdownMenuFieldTrigger>
            <DropdownMenuContent>
              {ASSET_TYPE_OPTIONS.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  selected={option.value === assetType}
                  onSelect={() => {
                    setAssetType(option.value);
                    setPage(1);
                  }}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuFieldTrigger>
              {SEVERITY_OPTIONS.find((o) => o.value === severity)?.label ?? "All severities"}
            </DropdownMenuFieldTrigger>
            <DropdownMenuContent>
              {SEVERITY_OPTIONS.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  selected={option.value === severity}
                  onSelect={() => {
                    setSeverity(option.value);
                    setPage(1);
                  }}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </Card>

      {loading ? (
        <PageSkeleton rows={6} />
      ) : error ? (
        <ErrorState message={apiErrorMessage(error)} />
      ) : data ? (
        <Card className="card-hover overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-left">
              <thead className="border-b border-zinc-200 bg-zinc-50 text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">
                <tr>
                  <th className="px-5 py-4">Asset</th>
                  <th className="px-4 py-4">Type</th>
                  <th className="px-4 py-4">Algorithm</th>
                  <th className="px-4 py-4">Location & evidence</th>
                  <th className="px-4 py-4">Risk</th>
                  <th className="px-5 py-4" />
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200">
                {data.items.map((asset) => (
                  <tr
                    key={asset.id}
                    onClick={() => setSelected(asset)}
                    className="interactive cursor-pointer text-sm hover:bg-zinc-50/80"
                  >
                    <td className="px-5 py-4">
                      <p className="font-semibold text-zinc-950">{asset.name}</p>
                      <p className="mt-0.5 font-mono text-xs text-zinc-500">{asset.project_name}</p>
                    </td>
                    <td className="px-4 py-4">
                      <span className="rounded border border-zinc-200 bg-zinc-100 px-2 py-0.5 font-mono text-[11px] font-medium capitalize text-zinc-700">
                        {asset.type}
                      </span>
                    </td>
                    <td className="px-4 py-4 font-mono text-xs font-semibold text-indigo-700">
                      {asset.algorithm ?? "—"}
                    </td>
                    <td className="max-w-md px-4 py-4">
                      <p className="truncate font-mono text-[11px] text-zinc-600">{asset.location}</p>
                      <p className="mt-0.5 truncate text-xs text-zinc-500">{asset.evidence}</p>
                    </td>
                    <td className="px-4 py-4">
                      {asset.risk ? (
                        <div className="flex items-center gap-2">
                          <SeverityBadge severity={asset.risk.severity} />
                          <span className="font-mono text-xs font-semibold text-zinc-600">
                            {Math.round(asset.risk.score)}
                          </span>
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <ExternalLink className="ml-auto h-4 w-4 text-zinc-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.items.length && (
            <EmptyState title="No matching assets" body="Adjust the filters or start a new discovery scan." />
          )}
          <div className="flex items-center justify-between border-t border-zinc-200 px-5 py-4 text-xs text-zinc-500">
            <span>
              {data.total
                ? `${(page - 1) * data.page_size + 1}–${Math.min(page * data.page_size, data.total)} of ${data.total}`
                : "0 assets"}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((value) => value - 1)}
                className="rounded border border-zinc-200 bg-white p-1.5 text-zinc-700 hover:bg-zinc-50 disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage((value) => value + 1)}
                className="rounded border border-zinc-200 bg-white p-1.5 text-zinc-700 hover:bg-zinc-50 disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
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
      <button className="absolute inset-0 bg-black/40 backdrop-blur-xs" onClick={close} aria-label="Close asset details" />
      <aside className="relative h-full w-full max-w-xl overflow-y-auto border-l border-zinc-200 bg-white p-6 shadow-2xl md:p-8">
        <button
          onClick={close}
          className="absolute right-5 top-5 rounded p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"
        >
          <X className="h-5 w-5" />
        </button>
        <span className="inline-flex rounded border border-indigo-200 bg-indigo-50 p-2.5 text-indigo-700">
          <FileSearch className="h-5 w-5" />
        </span>
        <p className="mt-5 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-600">{asset.type}</p>
        <h2 className="mt-2 pr-10 text-2xl font-bold tracking-tight text-zinc-950">{asset.name}</h2>
        <p className="mt-1 text-sm text-zinc-500">{asset.project_name}</p>
        {asset.risk && (
          <div className="mt-6 flex items-center justify-between rounded border border-zinc-200 bg-zinc-50 p-4">
            <div>
              <p className="font-mono text-xs text-zinc-500">Risk score</p>
              <p className="mt-0.5 text-2xl font-bold text-zinc-950">
                {Math.round(asset.risk.score)}
                <span className="font-mono text-sm font-normal text-zinc-400"> / 100</span>
              </p>
            </div>
            <SeverityBadge severity={asset.risk.severity} />
          </div>
        )}
        <dl className="mt-8 space-y-4 text-sm">
          <Detail label="Algorithm" value={asset.algorithm ?? "Not specified"} />
          <Detail label="Version" value={asset.version ?? "Not reported"} />
          <Detail label="Location" value={asset.location} mono />
          <Detail label="Evidence" value={asset.evidence} />
          <Detail label="Confidence" value={`${Math.round(asset.confidence * 100)}%`} />
          <Detail label="Dependent assets" value={String(asset.dependency_count)} />
        </dl>
        {asset.risk && (
          <div className="mt-8">
            <p className="font-mono text-xs font-bold uppercase tracking-wider text-zinc-500">Why this score</p>
            <ul className="mt-3 space-y-2">
              {asset.risk.reasons.map((reason) => (
                <li key={reason} className="flex gap-3 rounded border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-800">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-600" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded border border-zinc-100 bg-zinc-50/50 p-3">
      <dt className="mb-1 font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-500">{label}</dt>
      <dd className={`break-words text-sm font-medium text-zinc-900 ${mono ? "font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}

