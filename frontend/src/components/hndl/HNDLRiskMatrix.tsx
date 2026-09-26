import { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuFieldTrigger, DropdownMenuItem } from "../DropdownMenu";
import type { IntelligenceItem } from "../../types/api";

export type HNDLStatus = "at_risk" | "safe" | "low" | "monitor";

const STATUS_META: Record<HNDLStatus, { label: string; color: string; reason: (breakYear: number, lifetime: number) => string }> = {
  at_risk: {
    label: "At Risk",
    color: "var(--risk-critical)",
    reason: (breakYear, lifetime) => `data harvestable now, decryptable by ${breakYear} (${lifetime}-year retention)`,
  },
  safe: {
    label: "Safe",
    color: "var(--risk-low)",
    reason: () => "quantum-resistant algorithm",
  },
  low: {
    label: "Low",
    color: "var(--risk-medium)",
    reason: (_breakYear, lifetime) => `short ${lifetime}-year lifetime, expires before quantum arrival`,
  },
  monitor: {
    label: "Monitor",
    color: "var(--text-muted)",
    reason: (breakYear) => `re-assess as quantum arrival estimate (${breakYear}) firms up`,
  },
};

export interface HNDLRow {
  assetId: string;
  assetName: string;
  algorithm: string;
  sensitivity: string;
  dataLifetimeYears: number;
  quantumBreakYear: number;
  status: HNDLStatus;
}

/** Risk logic per issue #70 (unchanged from #24). */
export function classifyHNDL(params: { dataLifetimeYears: number; quantumSafe: boolean; yearsUntilQuantum: number }): HNDLStatus {
  const { dataLifetimeYears, quantumSafe, yearsUntilQuantum } = params;
  if (dataLifetimeYears < 1) return "low";
  if (quantumSafe) return "safe";
  if (dataLifetimeYears > yearsUntilQuantum) return "at_risk";
  return "monitor";
}

type SortKey = "assetName" | "dataLifetimeYears" | "quantumBreakYear" | "status";

const STATUS_ORDER: Record<HNDLStatus, number> = { at_risk: 0, monitor: 1, low: 2, safe: 3 };

export function HNDLRiskMatrix({ rows }: { rows: HNDLRow[] }) {
  const [statusFilter, setStatusFilter] = useState<HNDLStatus | "all">("all");
  const [sensitivityFilter, setSensitivityFilter] = useState<string>("all");
  const [algorithmFilter, setAlgorithmFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("status");
  const [sortAsc, setSortAsc] = useState(false);

  const sensitivities = useMemo(() => ["all", ...new Set(rows.map((r) => r.sensitivity))], [rows]);
  const algorithms = useMemo(() => ["all", ...new Set(rows.map((r) => r.algorithm))], [rows]);

  const filtered = useMemo(() => {
    return rows
      .filter((r) => statusFilter === "all" || r.status === statusFilter)
      .filter((r) => sensitivityFilter === "all" || r.sensitivity === sensitivityFilter)
      .filter((r) => algorithmFilter === "all" || r.algorithm === algorithmFilter)
      .sort((a, b) => {
        let cmp = 0;
        if (sortKey === "assetName") cmp = a.assetName.localeCompare(b.assetName);
        else if (sortKey === "dataLifetimeYears") cmp = a.dataLifetimeYears - b.dataLifetimeYears;
        else if (sortKey === "quantumBreakYear") cmp = a.quantumBreakYear - b.quantumBreakYear;
        else cmp = STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
        return sortAsc ? cmp : -cmp;
      });
  }, [rows, statusFilter, sensitivityFilter, algorithmFilter, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((v) => !v);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  const headerButton = (key: SortKey, label: string) => (
    <button
      onClick={() => toggleSort(key)}
      className="interactive inline-flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider"
      style={{ color: sortKey === key ? "var(--accent)" : "var(--text-muted)" }}
    >
      {label} <ArrowUpDown className="h-3 w-3" />
    </button>
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <DropdownMenu>
          <DropdownMenuFieldTrigger className="w-36">
            Status: {statusFilter === "all" ? "All" : STATUS_META[statusFilter].label}
          </DropdownMenuFieldTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem selected={statusFilter === "all"} onSelect={() => setStatusFilter("all")}>All</DropdownMenuItem>
            {(Object.keys(STATUS_META) as HNDLStatus[]).map((status) => (
              <DropdownMenuItem key={status} selected={statusFilter === status} onSelect={() => setStatusFilter(status)}>
                {STATUS_META[status].label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuFieldTrigger className="w-40">
            Sensitivity: {sensitivityFilter === "all" ? "All" : sensitivityFilter}
          </DropdownMenuFieldTrigger>
          <DropdownMenuContent>
            {sensitivities.map((s) => (
              <DropdownMenuItem key={s} selected={sensitivityFilter === s} onSelect={() => setSensitivityFilter(s)}>
                {s === "all" ? "All" : s}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuFieldTrigger className="w-40">
            Algorithm: {algorithmFilter === "all" ? "All" : algorithmFilter}
          </DropdownMenuFieldTrigger>
          <DropdownMenuContent>
            {algorithms.map((a) => (
              <DropdownMenuItem key={a} selected={algorithmFilter === a} onSelect={() => setAlgorithmFilter(a)}>
                {a === "all" ? "All" : a}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)" }}>
        <table className="w-full text-left text-xs">
          <thead>
            <tr style={{ background: "var(--bg-hover)" }}>
              <th className="px-3 py-2.5">{headerButton("assetName", "Asset")}</th>
              <th className="px-3 py-2.5 font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Algorithm</th>
              <th className="px-3 py-2.5 font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Sensitivity</th>
              <th className="px-3 py-2.5">{headerButton("dataLifetimeYears", "Data Lifetime")}</th>
              <th className="px-3 py-2.5">{headerButton("quantumBreakYear", "Quantum Break")}</th>
              <th className="px-3 py-2.5">{headerButton("status", "HNDL Status")}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, index) => {
              const meta = STATUS_META[row.status];
              return (
                <tr
                  key={row.assetId}
                  className="interactive"
                  style={{ background: index % 2 === 1 ? "var(--bg-hover)" : "transparent", borderTop: "1px solid var(--border)" }}
                >
                  <td className="px-3 py-2.5 font-medium" style={{ color: "var(--text-primary)" }}>{row.assetName}</td>
                  <td className="px-3 py-2.5 font-mono" style={{ color: "var(--text-secondary)" }}>{row.algorithm}</td>
                  <td className="px-3 py-2.5 capitalize" style={{ color: "var(--text-secondary)" }}>{row.sensitivity}</td>
                  <td className="px-3 py-2.5 tabular-nums" style={{ color: "var(--text-secondary)" }}>{row.dataLifetimeYears} yrs</td>
                  <td className="px-3 py-2.5 tabular-nums" style={{ color: "var(--text-secondary)" }}>{row.quantumBreakYear}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col gap-0.5">
                      <span
                        className="inline-flex w-fit items-center rounded-full px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider"
                        style={{ background: `color-mix(in srgb, ${meta.color} 14%, transparent)`, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {meta.reason(row.quantumBreakYear, row.dataLifetimeYears)}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="px-3 py-6 text-center text-xs" style={{ color: "var(--text-muted)" }}>No assets match the current filters.</p>
        )}
      </div>
    </div>
  );
}
