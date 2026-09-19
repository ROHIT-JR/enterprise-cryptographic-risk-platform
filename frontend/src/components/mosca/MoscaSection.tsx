import { useEffect, useState } from "react";
import { Gauge, MessageCircle } from "lucide-react";
import { moscaApi, apiErrorMessage } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import type { MoscaAssetResult } from "../../types/api";
import { Card, EmptyState, ErrorState, LoadingState } from "../ui";
import { MoscaTimeline } from "./MoscaTimeline";
import { MoscaControls } from "./MoscaControls";
import { AssetMoscaTable } from "./AssetMoscaTable";

export function MoscaSection() {
  const [quantumArrivalYear, setQuantumArrivalYear] = useState(2035);
  const [dataLifetime, setDataLifetime] = useState(20);
  const [migrationTime, setMigrationTime] = useState(3);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [ceoMode, setCeoMode] = useState(false);

  const { data, error, loading, reload } = useAsync(() => moscaApi.simulate(quantumArrivalYear), [quantumArrivalYear]);

  useEffect(() => {
    if (!data || selectedAssetId) return;
    const mostUrgent = data.items[0];
    if (mostUrgent) {
      setDataLifetime(mostUrgent.data_lifetime_years);
      setMigrationTime(mostUrgent.migration_time_years);
      setSelectedAssetId(mostUrgent.asset_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  function selectAsset(item: MoscaAssetResult) {
    setSelectedAssetId(item.asset_id);
    setDataLifetime(item.data_lifetime_years);
    setMigrationTime(item.migration_time_years);
  }

  if (loading && !data) return <LoadingState label="Running the Mosca inequality model" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const currentYear = data.current_year;
  const statusCopy: Record<typeof data.organization_status, { label: string; color: string }> = {
    critical: { label: "CRITICAL", color: "text-red-600" },
    plan: { label: "PLAN REQUIRED", color: "text-amber-600" },
    safe: { label: "SAFE", color: "text-emerald-600" },
  };
  const status = statusCopy[data.organization_status];

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-6">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-indigo-600">The core differentiator</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Mosca inequality: X + Y &gt; Z</h2>
          <p className="mt-1 text-xs text-slate-500">Does your migration finish before quantum computers arrive?</p>
        </div>
        <button
          onClick={() => setCeoMode((value) => !value)}
          className={`inline-flex items-center gap-2 self-start rounded-lg border px-3.5 py-2 text-xs font-semibold transition ${
            ceoMode ? "border-indigo-200 bg-indigo-50 text-indigo-700" : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
          }`}
        >
          <MessageCircle className="h-4 w-4" /> Explain to my CEO
        </button>
      </div>

      <div className="grid gap-6 p-5 md:p-6 xl:grid-cols-[1.5fr_1fr]">
        <div className="h-56">
          <MoscaTimeline
            dataLifetime={dataLifetime}
            migrationTime={migrationTime}
            quantumArrivalYear={quantumArrivalYear}
            currentYear={currentYear}
          />
        </div>
        <MoscaControls
          dataLifetime={dataLifetime}
          migrationTime={migrationTime}
          quantumArrivalYear={quantumArrivalYear}
          onDataLifetimeChange={setDataLifetime}
          onMigrationTimeChange={setMigrationTime}
          onQuantumArrivalYearChange={setQuantumArrivalYear}
        />
      </div>

      <div className="mx-5 mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4 md:mx-6 md:mb-6">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-indigo-600" />
          <p className="text-sm font-semibold text-slate-900">
            Organization status: <span className={status.color}>{status.label}</span>
          </p>
        </div>
        {ceoMode ? (
          <div className="mt-3 space-y-1.5 text-sm leading-6 text-slate-700">
            <p>Your most sensitive data needs to stay secret for about {dataLifetime} more years.</p>
            <p>Switching to quantum-safe encryption for that data will take roughly {migrationTime} years.</p>
            <p>
              Quantum computers capable of breaking today's encryption could arrive around {quantumArrivalYear}, which is{" "}
              {data.years_until_quantum} years from now.
            </p>
            <p className="font-medium text-slate-900">
              {data.critical_count} of {data.total_assets} systems will still be exposed when quantum computers arrive unless
              migration starts now.
            </p>
            {data.most_urgent_asset && <p>Most urgent: {data.most_urgent_asset}.</p>}
          </div>
        ) : (
          <div className="mt-3 space-y-1.5 text-sm text-slate-500">
            <p className="font-mono text-xs text-slate-500">{data.formula}</p>
            <p>
              {data.critical_count} critical · {data.plan_count} to plan · {data.safe_count} safe (of {data.total_assets} assets)
            </p>
            {data.most_urgent_asset && <p className="text-red-600">Most urgent: {data.most_urgent_asset}</p>}
          </div>
        )}
      </div>

      <div className="border-t border-slate-100 px-5 py-4 md:px-6">
        <p className="text-sm font-semibold text-slate-900">Per-asset Mosca breakdown</p>
        <p className="mt-1 text-xs text-slate-500">Click a row to load its values into the timeline above</p>
      </div>
      {data.items.length ? (
        <AssetMoscaTable
          items={data.items}
          yearsUntilQuantum={data.years_until_quantum}
          onSelect={selectAsset}
          selectedAssetId={selectedAssetId}
        />
      ) : (
        <EmptyState title="No assets analyzed yet" body="Complete a discovery scan to populate the Mosca breakdown." />
      )}
    </Card>
  );
}
