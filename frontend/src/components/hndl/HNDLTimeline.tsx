import { Building2, Database, ServerCrash, Unlock } from "lucide-react";

/**
 * 3-stage HNDL attack flow: Harvesting -> Storing -> Decrypting.
 * Uses the existing .animate-data-packet / .animate-decrypt keyframes from
 * index.css (already token-driven via the pulse-glow tokenization above)
 * rather than adding a duplicate animation for the same visual idea.
 */
export function HNDLTimeline({
  tbPerYear,
  algorithmsIntercepted,
  yearsHarvested,
  topAtRiskAsset,
}: {
  tbPerYear: number;
  algorithmsIntercepted: string[];
  yearsHarvested: number;
  topAtRiskAsset: string | null;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {/* Stage 1: Harvesting */}
      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4" style={{ color: "var(--accent)" }} />
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            Harvesting
          </p>
        </div>
        <div className="relative mt-3 flex h-10 items-center gap-1.5 overflow-hidden">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className="animate-data-packet h-2.5 w-4 shrink-0 rounded-sm"
              style={{ background: "var(--accent)", animationDelay: `${i * 0.5}s` }}
            />
          ))}
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          Encrypted data intercepted in transit
        </p>
        <p className="mt-1.5 text-lg font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>
          ~{tbPerYear} TB<span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>/year exposed</span>
        </p>
        {algorithmsIntercepted.length > 0 && (
          <p className="mt-1 truncate text-[11px]" style={{ color: "var(--text-muted)" }}>
            {algorithmsIntercepted.slice(0, 3).join(", ")}
          </p>
        )}
      </div>

      {/* Stage 2: Storing */}
      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4" style={{ color: "var(--risk-high)" }} />
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            Storing
          </p>
        </div>
        <div className="mt-3 flex h-10 items-end gap-1">
          {[30, 45, 60, 75, 90].map((h, i) => (
            <span
              key={i}
              className="w-full rounded-t-sm"
              style={{ height: `${h}%`, background: `color-mix(in srgb, var(--risk-high) ${40 + i * 12}%, transparent)` }}
            />
          ))}
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          Data stored until quantum decryption is possible
        </p>
        <p className="mt-1.5 text-lg font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>
          {yearsHarvested} <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>years of accumulation</span>
        </p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
          Storage cost to adversary: pennies per GB
        </p>
      </div>

      {/* Stage 3: Decrypting */}
      <div className="rounded-xl border p-4" style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 6%, transparent)" }}>
        <div className="flex items-center gap-2">
          <Unlock className="h-4 w-4" style={{ color: "var(--risk-critical)" }} />
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--risk-critical)" }}>
            Decrypting
          </p>
        </div>
        <div className="mt-3 flex h-10 items-center justify-center">
          <ServerCrash className="animate-decrypt h-8 w-8" style={{ color: "var(--risk-critical)" }} />
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          Quantum computer breaks the encryption
        </p>
        <p className="mt-1.5 truncate text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          {topAtRiskAsset ?? "Long-lived records"} → fully exposed
        </p>
        <p className="mt-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
          Customer PII, financial records, trade secrets
        </p>
      </div>
    </div>
  );
}
