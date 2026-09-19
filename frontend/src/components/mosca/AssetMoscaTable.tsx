import type { MoscaAssetResult, MoscaVerdict } from "../../types/api";
import { EmptyState } from "../ui";

const VERDICT_STYLES: Record<MoscaVerdict, string> = {
  critical: "border-red-200 bg-red-50 text-red-700",
  plan: "border-amber-200 bg-amber-50 text-amber-700",
  safe: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

const VERDICT_LABEL: Record<MoscaVerdict, string> = {
  critical: "Critical",
  plan: "Plan",
  safe: "Safe",
};

interface AssetMoscaTableProps {
  items: MoscaAssetResult[];
  yearsUntilQuantum: number;
  onSelect: (item: MoscaAssetResult) => void;
  selectedAssetId: string | null;
}

export function AssetMoscaTable({ items, yearsUntilQuantum, onSelect, selectedAssetId }: AssetMoscaTableProps) {
  if (!items.length) {
    return <EmptyState title="No assets to evaluate" body="Run a discovery scan to populate the Mosca breakdown." />;
  }
  return (
    <div className="divide-y divide-slate-100">
      {items.slice(0, 25).map((item) => (
        <button
          key={item.asset_id}
          onClick={() => onSelect(item)}
          className={`grid w-full grid-cols-[1fr_110px_90px_90px_90px] items-center gap-3 px-5 py-3 text-left text-sm transition hover:bg-slate-50 md:px-6 ${
            selectedAssetId === item.asset_id ? "bg-indigo-50/50" : ""
          }`}
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-900">{item.asset_name}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-500">{item.algorithm ?? "—"}</p>
          </div>
          <p className="text-xs text-slate-500">{item.data_lifetime_years}y lifetime</p>
          <p className="text-xs text-slate-500">{item.migration_time_years}y migrate</p>
          <p className="text-xs text-slate-500">
            {item.lhs} <span className="text-slate-400">vs {yearsUntilQuantum}</span>
          </p>
          <span className={`inline-flex justify-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${VERDICT_STYLES[item.verdict]}`}>
            {VERDICT_LABEL[item.verdict]}
          </span>
        </button>
      ))}
    </div>
  );
}
