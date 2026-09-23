import { useEffect, useState } from "react";
import { ArrowRight, Cpu, Gauge, Info, Link2, Play, X } from "lucide-react";
import { benchmarksApi } from "../../api/client";
import { Card, SeverityBadge } from "../ui";
import type { MigrationImpact, MigrationRecommendation, Severity } from "../../types/api";

// The benchmarks API (backend/app/api/benchmarks.py -> config/pqc_benchmarks.json,
// cited to FIPS-203/204/205) only knows these exact algorithm keys. Assets'
// current_algorithm/recommended_algorithm strings are free text from the
// scanner, so this maps them onto the closest known key. Where a swap only
// changes one side of a TLS handshake (e.g. just the KEX), the other side is
// held at a representative default pairing (ECDH-P256/RSA-2048 -> ML-KEM-768/
// ML-DSA-65) rather than guessed — documented here, not silently assumed.
const KNOWN_ALGORITHMS = [
  "ML-KEM-512", "ML-KEM-768", "ML-KEM-1024",
  "ML-DSA-65", "ML-DSA-87", "SLH-DSA-SHA2-128f",
  "RSA-4096", "RSA-2048", "ECDSA-P256", "ECDH-P256",
];

function normalizeAlgorithm(raw: string): string | null {
  const upper = raw.toUpperCase().replace(/_/g, "-");
  return KNOWN_ALGORITHMS.find((known) => upper.includes(known.toUpperCase())) ?? null;
}

function isKemTarget(name: string) {
  return /KEM|ECDH|DIFFIE/i.test(name);
}

function complexityToSeverity(c: string): Severity {
  if (c === "critical") return "critical";
  if (c === "high") return "high";
  if (c === "medium") return "medium";
  return "low";
}

function formatUs(us: number): string {
  if (us >= 1000) return `${(us / 1000).toFixed(2)} ms`;
  return `${us.toFixed(1)} µs`;
}

export function TaskDetail({
  item,
  waveTitle,
  onClose,
}: {
  item: MigrationRecommendation;
  waveTitle: string;
  onClose: () => void;
}) {
  const [impact, setImpact] = useState<MigrationImpact | null>(null);
  const [impactError, setImpactError] = useState<string | null>(null);

  useEffect(() => {
    setImpact(null);
    setImpactError(null);
    const recommendedKnown = normalizeAlgorithm(item.recommended_algorithm);
    const currentKnown = normalizeAlgorithm(item.current_algorithm);
    if (!recommendedKnown) {
      setImpactError("Performance benchmark data isn't available for this target algorithm.");
      return;
    }
    const targetIsKem = isKemTarget(recommendedKnown);
    const query = targetIsKem
      ? {
          kex_from: currentKnown && isKemTarget(currentKnown) ? currentKnown : "ECDH-P256",
          kex_to: recommendedKnown,
          auth_from: "RSA-2048",
          auth_to: "ML-DSA-65",
          chain_certs: 2,
        }
      : {
          kex_from: "ECDH-P256",
          kex_to: "ML-KEM-768",
          auth_from: currentKnown && !isKemTarget(currentKnown) ? currentKnown : "RSA-2048",
          auth_to: recommendedKnown,
          chain_certs: 2,
        };
    benchmarksApi.migrationImpact(query).then(setImpact).catch(() => setImpactError("Could not load benchmark comparison."));
  }, [item.recommended_algorithm, item.current_algorithm]);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b px-5 py-3.5" style={{ borderColor: "var(--border)" }}>
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>{waveTitle}</p>
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{item.asset_name}</p>
        </div>
        <button onClick={onClose} className="interactive rounded p-1 hover:bg-[var(--bg-hover)]" style={{ color: "var(--text-muted)" }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-4 p-5 md:grid-cols-2">
        <div>
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Algorithm swap</p>
          <div className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            <span className="font-mono">{item.current_algorithm}</span>
            <ArrowRight className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--accent)" }} />
            <span className="font-mono">{item.recommended_algorithm}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <SeverityBadge severity={complexityToSeverity(item.complexity)} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            <Link2 className="mr-1 inline h-3 w-3" />{item.dependent_systems} affected services
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            <Gauge className="mr-1 inline h-3 w-3" />~{item.estimated_hours}h estimated
          </span>
        </div>
      </div>

      {/* Performance impact — real numbers via /benchmarks/migration-impact */}
      <div className="border-t px-5 py-4" style={{ borderColor: "var(--border)" }}>
        <p className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          <Cpu className="h-3.5 w-3.5" /> Performance impact (measured reference data, FIPS-203/204/205)
        </p>
        {impactError && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{impactError}</p>}
        {impact && (
          <div className="grid grid-cols-3 gap-2.5 text-xs">
            <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>Handshake CPU time</p>
              <p className="mt-0.5 font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                {formatUs(impact.before.total_cpu_us)} → {formatUs(impact.after.total_cpu_us)}
              </p>
              <p style={{ color: impact.delta.cpu_percent > 0 ? "var(--risk-high)" : "var(--risk-low)" }}>
                {impact.delta.cpu_percent > 0 ? "+" : ""}{impact.delta.cpu_percent.toFixed(0)}%
              </p>
            </div>
            <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>Handshake bytes</p>
              <p className="mt-0.5 font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                {impact.before.total_bytes} B → {impact.after.total_bytes} B
              </p>
              <p style={{ color: impact.delta.bytes_percent > 0 ? "var(--risk-high)" : "var(--risk-low)" }}>
                {impact.delta.bytes_percent > 0 ? "+" : ""}{impact.delta.bytes_percent.toFixed(0)}%
              </p>
            </div>
            <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>Certificate chain</p>
              <p className="mt-0.5 font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                {impact.before.certificate_chain_bytes} B → {impact.after.certificate_chain_bytes} B
              </p>
              <p style={{ color: impact.delta.certificate_chain_percent > 0 ? "var(--risk-high)" : "var(--risk-low)" }}>
                {impact.delta.certificate_chain_percent > 0 ? "+" : ""}{impact.delta.certificate_chain_percent.toFixed(0)}%
              </p>
            </div>
          </div>
        )}
        {impact && (
          <p className="mt-2 flex items-start gap-1.5 text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
            <Info className="mt-0.5 h-3 w-3 shrink-0" /> {impact.assumptions.note}
          </p>
        )}
      </div>

      {/* Hybrid migration recommendation */}
      <div className="border-t px-5 py-4" style={{ borderColor: "var(--border)" }}>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Recommended migration path</p>
        <ol className="space-y-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          <li><strong style={{ color: "var(--text-primary)" }}>Step 1.</strong> Add {item.recommended_algorithm} alongside {item.current_algorithm} ({item.recommendation.hybrid_strategy ?? "dual-stack support"})</li>
          <li><strong style={{ color: "var(--text-primary)" }}>Step 2.</strong> Run hybrid mode for 30 days, monitoring compatibility and performance</li>
          <li><strong style={{ color: "var(--text-primary)" }}>Step 3.</strong> Remove {item.current_algorithm}, PQC-only</li>
        </ol>
        {item.reasons.length > 0 && (
          <div className="mt-3">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Dependencies</p>
            <ul className="list-inside list-disc space-y-0.5 text-xs" style={{ color: "var(--text-secondary)" }}>
              {item.reasons.map((reason, i) => <li key={i}>{reason}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div className="flex gap-2 border-t px-5 py-4" style={{ borderColor: "var(--border)" }}>
        <button className="interactive btn-primary flex-1 justify-between">
          Start Migration <Play className="h-3.5 w-3.5" />
        </button>
        <button className="interactive btn-secondary">
          View Details <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </Card>
  );
}
