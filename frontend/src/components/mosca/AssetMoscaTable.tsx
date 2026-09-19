import type { MoscaAssetResult, MoscaVerdict } from "../../types/api";
import { EmptyState } from "../ui";

const VERDICT_STYLES: Record<MoscaVerdict, string> = {
  critical: "border-rose-400/25 bg-rose-500/10 text-rose-300",
  plan: "border-amber-400/25 bg-amber-500/10 text-amber-200",
  safe: "border-emerald-400/25 bg-emerald-500/10 text-emerald-300",
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
    <div className="divide-y divide-white/[0.05]">
      {items.slice(0, 25).map((item) => (
        <button
          key={item.asset_id}
          onClick={() => onSelect(item)}
          className={`grid w-full grid-cols-[1fr_110px_90px_90px_90px] items-center gap-3 px-5 py-3 text-left text-sm transition hover:bg-white/[0.03] md:px-6 ${
            selectedAssetId === item.asset_id ? "bg-brand-400/[0.05]" : ""
          }`}
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-200">{item.asset_name}</p>
            <p className="mt-0.5 font-mono text-xs text-slate-600">{item.algorithm ?? "—"}</p>
          </div>
          <p className="text-xs text-slate-500">{item.data_lifetime_years}y lifetime</p>
          <p className="text-xs text-slate-500">{item.migration_time_years}y migrate</p>
          <p className="text-xs text-slate-500">
            {item.lhs} <span className="text-slate-700">vs {yearsUntilQuantum}</span>
          </p>
          <span className={`inline-flex justify-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${VERDICT_STYLES[item.verdict]}`}>
            {VERDICT_LABEL[item.verdict]}
          </span>
        </button>
      ))}
    </div>
  );
}
