import { Gauge, Play, ShieldCheck, ShieldOff } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiErrorMessage, benchmarksApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type {
  BenchmarkAlgorithm,
  BenchmarkCatalogue,
  BenchmarkTimings,
  MigrationImpact,
  MigrationImpactQuery,
} from "../types/api";

const ALGORITHM_COLORS: Record<string, string> = {
  "ML-KEM-512": "#6366f1",
  "ML-KEM-768": "#4f46e5",
  "ML-KEM-1024": "#7c3aed",
  "ML-DSA-65": "#0891b2",
  "ML-DSA-87": "#0d9488",
  "SLH-DSA-SHA2-128f": "#16a34a",
  "RSA-2048": "#dc2626",
  "RSA-4096": "#ea580c",
  "ECDSA-P256": "#ca8a04",
  "ECDH-P256": "#71717a",
};
const FALLBACK_COLOR = "#52525b";
const DEFAULT_RADAR = ["RSA-2048", "ECDSA-P256", "ML-KEM-768", "ML-DSA-65"];
const RADAR_AXES: { key: keyof BenchmarkAlgorithm["scores"]; label: string }[] = [
  { key: "speed", label: "Speed" },
  { key: "compactness", label: "Compactness" },
  { key: "maturity", label: "Maturity" },
  { key: "quantum_security", label: "Quantum security" },
];
const RUN_ROLES = ["administrator", "security_analyst"];
const LIVE_RUN_ITERATIONS = 20;

type DataSource = "reference" | "live";

const colorOf = (name: string) => ALGORITHM_COLORS[name] ?? FALLBACK_COLOR;

function formatMicros(us: number): string {
  if (us >= 1_000_000) return `${+(us / 1_000_000).toFixed(2)} s`;
  if (us >= 1_000) return `${+(us / 1_000).toFixed(2)} ms`;
  return `${+us.toFixed(us < 10 ? 2 : 0)} µs`;
}

function formatBytes(bytes: number): string {
  // Decimal kilobytes: the TLS congestion-window figure (10 × 1460 B) is decimal too.
  return bytes >= 10_000 ? `${(bytes / 1000).toFixed(1)} KB` : `${bytes.toLocaleString("en")} B`;
}

function formatPercent(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toLocaleString("en", { maximumFractionDigits: 1 })}%`;
}

/** The two operations a party performs, in the order they are plotted. */
function operationPair(kind: BenchmarkAlgorithm["kind"], timings: Partial<BenchmarkTimings>) {
  return kind === "kem"
    ? { first: timings.encaps_us, second: timings.decaps_us }
    : { first: timings.sign_us, second: timings.verify_us };
}

function logTicks(max: number): number[] {
  const ticks: number[] = [];
  for (let value = 1; value < max * 10; value *= 10) ticks.push(value);
  return ticks;
}

function LogAxis({ max }: { max: number }) {
  const ticks = logTicks(max);
  return (
    <YAxis
      scale="log"
      domain={[1, ticks[ticks.length - 1] ?? 10]}
      ticks={ticks}
      allowDataOverflow
      tickFormatter={formatMicros}
      tick={{ fontSize: 10, fill: "#71717a" }}
      width={62}
      stroke="#d4d4d8"
    />
  );
}

const SOURCE_LABELS: Record<string, { label: string; style: string }> = {
  estimate: { label: "estimate", style: "border-amber-300 bg-amber-50 text-amber-900" },
  "derived-liboqs-ratio": { label: "derived", style: "border-sky-300 bg-sky-50 text-sky-900" },
  "measured-liboqs-scaled": { label: "scaled", style: "border-sky-300 bg-sky-50 text-sky-900" },
};
const DEFAULT_SOURCE_LABEL = { label: "reference", style: "border-zinc-300 bg-zinc-50 text-zinc-700" };

function SourceBadge({ source }: { source: string }) {
  const { label, style } = SOURCE_LABELS[source] ?? DEFAULT_SOURCE_LABEL;
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${style}`}
    >
      {label}
    </span>
  );
}

// ─────────────────────────────────────────────
// Charts
// ─────────────────────────────────────────────
interface ChartRow {
  name: string;
  value: number;
  live: boolean;
}

function ChartCard({ title, caption, children }: { title: string; caption: string; children: React.ReactNode }) {
  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold text-zinc-950">{title}</h2>
      <p className="mt-0.5 mb-3 text-[11px] leading-normal text-zinc-500">{caption}</p>
      {children}
    </Card>
  );
}

function KeygenChart({ rows }: { rows: ChartRow[] }) {
  const max = Math.max(...rows.map((row) => row.value), 1);
  return (
    <div className="h-72" role="img" aria-label="Key generation time by algorithm, logarithmic scale">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="#f4f4f5" vertical={false} />
          <XAxis dataKey="name" interval={0} angle={-25} textAnchor="end" height={54} tick={{ fontSize: 10, fill: "#52525b" }} />
          <LogAxis max={max} />
          <Tooltip formatter={(value) => formatMicros(Number(value))} cursor={{ fill: "#f4f4f5" }} />
          <Bar dataKey="value" name="Key generation" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {rows.map((row) => (
              <Cell key={row.name} fill={colorOf(row.name)} fillOpacity={row.live ? 1 : 0.55} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function OperationChart({ rows }: { rows: { name: string; first: number; second: number }[] }) {
  const max = Math.max(...rows.flatMap((row) => [row.first, row.second]), 1);
  return (
    <div className="h-72" role="img" aria-label="Operation time by algorithm, logarithmic scale">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="#f4f4f5" vertical={false} />
          <XAxis dataKey="name" interval={0} angle={-25} textAnchor="end" height={54} tick={{ fontSize: 10, fill: "#52525b" }} />
          <LogAxis max={max} />
          <Tooltip formatter={(value) => formatMicros(Number(value))} cursor={{ fill: "#f4f4f5" }} />
          <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="first" name="Encapsulate / Sign" fill="#4f46e5" isAnimationActive={false} radius={[3, 3, 0, 0]} />
          <Bar dataKey="second" name="Decapsulate / Verify" fill="#a1a1aa" isAnimationActive={false} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SizeTable({ algorithms }: { algorithms: BenchmarkAlgorithm[] }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-xs">
        <caption className="sr-only">Key, ciphertext and signature sizes per algorithm</caption>
        <thead>
          <tr className="border-b border-zinc-200 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
            <th scope="col" className="px-4 py-2.5 font-medium">Algorithm</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Use</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Public key</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Private key</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Ciphertext / signature</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Security</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Quantum-safe</th>
          </tr>
        </thead>
        <tbody>
          {algorithms.map((algorithm) => {
            const { sizes_bytes: sizes } = algorithm;
            return (
              <tr key={algorithm.name} className="border-b border-zinc-100 last:border-0">
                <th scope="row" className="px-4 py-2.5 font-mono font-semibold text-zinc-900">
                  <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: colorOf(algorithm.name) }} />
                  {algorithm.name}
                </th>
                <td className="px-3 py-2.5 text-zinc-600">{algorithm.kind === "kem" ? "Key exchange" : "Signature"}</td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums">{formatBytes(sizes.pk_bytes)}</td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums">{formatBytes(sizes.sk_bytes)}</td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                  {formatBytes(sizes.ct_bytes ?? sizes.sig_bytes ?? 0)}
                </td>
                <td className="px-3 py-2.5 text-zinc-600">
                  {algorithm.nist_category !== null
                    ? `NIST level ${algorithm.nist_category}`
                    : `~${algorithm.classical_security_bits}-bit classical`}
                </td>
                <td className="px-4 py-2.5">
                  {algorithm.quantum_safe ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700">
                      <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Yes
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-red-700">
                      <ShieldOff className="h-3.5 w-3.5" aria-hidden /> No (Shor)
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function RadarComparison({ algorithms }: { algorithms: BenchmarkAlgorithm[] }) {
  const [selected, setSelected] = useState<string[]>(DEFAULT_RADAR);
  const chosen = algorithms.filter((algorithm) => selected.includes(algorithm.name));
  const data = RADAR_AXES.map(({ key, label }) => ({
    axis: label,
    ...Object.fromEntries(chosen.map((algorithm) => [algorithm.name, algorithm.scores[key]])),
  }));
  const toggle = (name: string) =>
    setSelected((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]));

  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold text-zinc-950">Multi-dimensional comparison</h2>
      <p className="mt-0.5 text-[11px] leading-normal text-zinc-500">
        Scores are 0–100, computed from the reference data so algorithms stay comparable.
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="Algorithms shown on the radar chart">
        {algorithms.map((algorithm) => {
          const active = selected.includes(algorithm.name);
          return (
            <button
              key={algorithm.name}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(algorithm.name)}
              className={`rounded border px-2 py-1 font-mono text-[11px] transition ${
                active ? "border-zinc-900 bg-zinc-900 text-white" : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              <span className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle" style={{ background: colorOf(algorithm.name) }} />
              {algorithm.name}
            </button>
          );
        })}
      </div>
      {chosen.length === 0 ? (
        <EmptyState title="Pick at least one algorithm" body="Select algorithms above to plot them." />
      ) : (
        <div className="h-80" role="img" aria-label="Radar chart of speed, compactness, maturity and quantum security">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data} outerRadius="72%">
              <PolarGrid stroke="#e4e4e7" />
              <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: "#3f3f46" }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#a1a1aa" }} angle={90} />
              {chosen.map((algorithm) => (
                <Radar
                  key={algorithm.name}
                  name={algorithm.name}
                  dataKey={algorithm.name}
                  stroke={colorOf(algorithm.name)}
                  fill={colorOf(algorithm.name)}
                  fillOpacity={0.12}
                  isAnimationActive={false}
                />
              ))}
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
      <dl className="mt-3 grid gap-x-6 gap-y-1 text-[11px] leading-normal text-zinc-500 sm:grid-cols-2">
        <div><dt className="inline font-medium text-zinc-700">Speed</dt> — handshake operations (encapsulate + decapsulate, or sign + verify), log-scaled.</div>
        <div><dt className="inline font-medium text-zinc-700">Compactness</dt> — public key plus ciphertext or signature, log-scaled.</div>
        <div><dt className="inline font-medium text-zinc-700">Maturity</dt> — years since standardisation, capped at 25.</div>
        <div><dt className="inline font-medium text-zinc-700">Quantum security</dt> — NIST category × 20; 0 if Shor&apos;s algorithm breaks it.</div>
      </dl>
    </Card>
  );
}

// ─────────────────────────────────────────────
// Migration impact calculator
// ─────────────────────────────────────────────
function ImpactMetric({
  label,
  before,
  after,
  change,
}: {
  label: string;
  before: string;
  after: string;
  change: string;
}) {
  return (
    <div className="rounded border border-zinc-200 bg-zinc-50/60 p-3">
      <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-1.5 flex flex-wrap items-baseline gap-x-2 font-mono text-sm text-zinc-950">
        <span className="text-zinc-500">{before}</span>
        <span aria-hidden>→</span>
        <span className="sr-only">to</span>
        <span className="font-semibold">{after}</span>
      </p>
      <p className="mt-1 font-mono text-xs text-indigo-700">{change}</p>
    </div>
  );
}

function SafetyChip({ label, safe }: { label: string; safe: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] ${
        safe ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900"
      }`}
    >
      {safe ? <ShieldCheck className="h-3 w-3" aria-hidden /> : <ShieldOff className="h-3 w-3" aria-hidden />}
      {label}: {safe ? "quantum-safe" : "quantum-vulnerable"}
    </span>
  );
}

function describeChange(percent: number, faster: string, slower: string): string {
  if (Math.abs(percent) < 0.05) return "no change";
  return `${Math.abs(percent).toLocaleString("en", { maximumFractionDigits: 1 })}% ${percent < 0 ? faster : slower}`;
}

function MigrationCalculator({ catalogue }: { catalogue: BenchmarkCatalogue }) {
  // RSA can also be used the legacy way (client encrypts the pre-master secret): the issue's
  // "RSA-2048 → ML-KEM-768" example.
  const keyExchanges = catalogue.algorithms.filter(
    (algorithm) => algorithm.kind === "kem" || algorithm.family === "RSA",
  );
  const signatures = catalogue.algorithms.filter((algorithm) => algorithm.kind === "signature");
  const [query, setQuery] = useState<MigrationImpactQuery>({
    kex_from: "ECDH-P256",
    kex_to: "ML-KEM-768",
    auth_from: "RSA-2048",
    auth_to: "ML-DSA-65",
    chain_certs: catalogue.tls_model.default_chain_certs,
  });
  const [impact, setImpact] = useState<MigrationImpact | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    benchmarksApi
      .migrationImpact(query)
      .then((result) => !cancelled && setImpact(result))
      .catch((caught) => !cancelled && setError(apiErrorMessage(caught)));
    return () => {
      cancelled = true;
    };
  }, [query]);

  const select = (label: string, key: keyof MigrationImpactQuery, options: BenchmarkAlgorithm[]) => (
    <label className="block">
      <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-zinc-500">{label}</span>
      <select
        className="field"
        value={query[key]}
        onChange={(event) => setQuery((current) => ({ ...current, [key]: event.target.value }))}
      >
        {options.map((algorithm) => (
          <option key={algorithm.name} value={algorithm.name}>
            {algorithm.name}
            {key.startsWith("kex") && algorithm.kind === "signature" ? " (key transport)" : ""}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold text-zinc-950">Migration impact calculator</h2>
      <p className="mt-0.5 text-[11px] leading-normal text-zinc-500">
        Models one full TLS 1.3 handshake before and after swapping the key exchange and the certificate signatures.
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {select("Key exchange — current", "kex_from", keyExchanges)}
        {select("Key exchange — target", "kex_to", keyExchanges)}
        {select("Certificates — current", "auth_from", signatures)}
        {select("Certificates — target", "auth_to", signatures)}
        <label className="block">
          <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-zinc-500">Chain length</span>
          <select
            className="field"
            value={query.chain_certs}
            onChange={(event) => setQuery((current) => ({ ...current, chain_certs: Number(event.target.value) }))}
          >
            {[1, 2, 3, 4].map((count) => (
              <option key={count} value={count}>
                {count} certificate{count > 1 ? "s" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p role="alert" className="mt-4 font-mono text-xs text-red-700">{error}</p>}
      {impact && !error && (
        <div className="mt-4 space-y-3" aria-live="polite">
          <div className="grid gap-3 md:grid-cols-3">
            <ImpactMetric
              label="Handshake CPU (client + server)"
              before={formatMicros(impact.before.total_cpu_us)}
              after={formatMicros(impact.after.total_cpu_us)}
              change={describeChange(impact.delta.cpu_percent, "faster", "slower")}
            />
            <ImpactMetric
              label="Bytes on the wire"
              before={formatBytes(impact.before.total_bytes)}
              after={formatBytes(impact.after.total_bytes)}
              change={`${formatPercent(impact.delta.bytes_percent)} (${impact.delta.bytes >= 0 ? "+" : "−"}${formatBytes(Math.abs(impact.delta.bytes))})`}
            />
            <ImpactMetric
              label="Certificate chain size"
              before={formatBytes(impact.before.certificate_chain_bytes)}
              after={formatBytes(impact.after.certificate_chain_bytes)}
              change={formatPercent(impact.delta.certificate_chain_percent)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <SafetyChip label="Key exchange" safe={impact.after.key_exchange_quantum_safe} />
            <SafetyChip label="Authentication" safe={impact.after.authentication_quantum_safe} />
          </div>

          {impact.after.exceeds_initial_cwnd && !impact.before.exceeds_initial_cwnd && (
            <p className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs leading-normal text-amber-950">
              The server&apos;s first flight grows to {formatBytes(impact.after.server_flight_bytes)}, beyond a typical{" "}
              {formatBytes(impact.assumptions.initial_congestion_window_bytes)} initial congestion window, so expect an
              extra network round trip on new connections.
            </p>
          )}
          {(impact.before.key_exchange_mode === "rsa-key-transport" ||
            impact.after.key_exchange_mode === "rsa-key-transport") && (
            <p className="text-[11px] leading-normal text-zinc-500">
              RSA key exchange here means legacy key transport (TLS 1.2 style): the client encrypts the pre-master
              secret to the server&apos;s certificate key, so there is no key generation and no key share on the wire.
              TLS 1.3 has no RSA key exchange.
            </p>
          )}
          <p className="text-[11px] leading-normal text-zinc-500">
            {impact.assumptions.note} Each certificate adds {impact.assumptions.cert_overhead_bytes} bytes of X.509
            overhead. Network latency is not modelled.
          </p>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────
export function PQCBenchmarks() {
  const { user } = useAuth();
  const { data, error, loading, reload, setData } = useAsync(() => benchmarksApi.pqc(), []);
  const [source, setSource] = useState<DataSource>("reference");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const canRun = user !== null && RUN_ROLES.includes(user.role);

  const algorithms = data?.algorithms;
  const live = source === "live" && data?.latest_run !== null && data?.latest_run !== undefined;

  const keygenRows = useMemo<ChartRow[]>(
    () =>
      (algorithms ?? []).map((algorithm) => {
        const measured = live ? algorithm.measured_us?.keygen_us : undefined;
        return { name: algorithm.name, value: measured ?? algorithm.timings_us.keygen_us, live: measured !== undefined };
      }),
    [algorithms, live],
  );
  const operationRows = useMemo(
    () =>
      (algorithms ?? []).map((algorithm) => {
        const measured = live && algorithm.measured_us ? operationPair(algorithm.kind, algorithm.measured_us) : null;
        const reference = operationPair(algorithm.kind, algorithm.timings_us);
        return {
          name: algorithm.name,
          first: measured?.first ?? reference.first ?? 0,
          second: measured?.second ?? reference.second ?? 0,
        };
      }),
    [algorithms, live],
  );

  if (loading) return <LoadingState label="Loading PQC benchmark data" />;
  if (error || !data || !algorithms) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const run = data.latest_run;
  const referenceOnly = algorithms.filter((algorithm) => live && algorithm.measured_us === null);
  const estimatedShown = algorithms.filter(
    (algorithm) => algorithm.timing_source === "estimate" && !(live && algorithm.measured_us),
  );

  async function runBenchmark() {
    setRunning(true);
    setRunError(null);
    try {
      setData(await benchmarksApi.run(LIVE_RUN_ITERATIONS));
      setSource("live");
    } catch (caught) {
      setRunError(apiErrorMessage(caught));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Research"
        title="PQC Performance Benchmarks"
        description="Post-quantum key exchange and signatures compared with the RSA and elliptic-curve algorithms they replace: speed, sizes, and what a migration costs a TLS handshake."
        action={
          canRun && (
            <button type="button" className="btn-primary" onClick={() => void runBenchmark()} disabled={running}>
              <Play className="h-3.5 w-3.5" aria-hidden />
              {running ? "Benchmarking…" : "Run live benchmark"}
            </button>
          )
        }
      />

      {runError && <p role="alert" className="font-mono text-xs text-red-700">{runError}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded border border-zinc-200 bg-white p-0.5" role="group" aria-label="Timing data source">
          {(["reference", "live"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={source === option}
              disabled={option === "live" && !run}
              onClick={() => setSource(option)}
              className={`segment-tab rounded ${
                source === option ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-50"
              } disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {option === "reference" ? "NIST reference" : "Live run on server"}
            </button>
          ))}
        </div>
        {!run && (
          <span className="text-[11px] text-zinc-500">
            {canRun ? "Run a live benchmark to compare against this server's hardware." : "No live run yet."}
          </span>
        )}
      </div>

      {live && run && (
        <Card className="flex gap-3 border-indigo-200 bg-indigo-50/40 p-3">
          <Gauge className="mt-0.5 h-4 w-4 shrink-0 text-indigo-700" aria-hidden />
          <p className="text-xs leading-normal text-zinc-700">
            Live run: {run.iterations} iterations in {run.duration_s}s on {run.environment.platform} (
            {run.environment.machine}), Python {run.environment.python}, cryptography{" "}
            {run.environment.cryptography ?? "unknown"}.{" "}
            {referenceOnly.length > 0 && (
              <>
                {referenceOnly.map((algorithm) => algorithm.name).join(", ")} could not be measured
                {run.environment.oqs_available ? "" : " (liboqs is not installed)"} and are shown faded from the
                reference data, so compare them with the measured classical bars with care: they come from different
                hardware.
              </>
            )}
          </p>
        </Card>
      )}

      {estimatedShown.length > 0 && (
        <p className="text-[11px] leading-normal text-zinc-500">
          <span className="font-medium text-zinc-700">Estimates:</span> timings for{" "}
          {estimatedShown.map((algorithm) => algorithm.name).join(", ")} are order-of-magnitude figures, not NIST
          citations. Sizes are exact (FIPS 203/204). See Data sources below.
        </p>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <ChartCard
          title="Key generation time"
          caption="Log scale — RSA key generation is three to four orders of magnitude slower than lattice-based schemes."
        >
          <KeygenChart rows={keygenRows} />
        </ChartCard>
        <ChartCard
          title="Operation time"
          caption="Key exchange: encapsulate vs decapsulate. Signatures: sign vs verify. Log scale."
        >
          <OperationChart rows={operationRows} />
        </ChartCard>
      </div>

      <section aria-labelledby="sizes-heading" className="space-y-2">
        <h2 id="sizes-heading" className="text-sm font-semibold text-zinc-950">
          Key, ciphertext and signature sizes
        </h2>
        <SizeTable algorithms={algorithms} />
      </section>

      <RadarComparison algorithms={algorithms} />
      <MigrationCalculator catalogue={data} />

      <Card className="p-4">
        <h2 className="text-sm font-semibold text-zinc-950">Data sources</h2>
        <ul className="mt-2 space-y-1 text-[11px] leading-normal text-zinc-600">
          {Object.entries(data.sources).map(([key, text]) => (
            <li key={key}>
              <span className="font-mono font-medium text-zinc-800">{key}</span> — {text}
            </li>
          ))}
        </ul>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-zinc-600">
          {algorithms.map((algorithm) => (
            <span key={algorithm.name} className="inline-flex items-center gap-1.5">
              <span className="font-mono">{algorithm.name}</span>
              <SourceBadge source={algorithm.timing_source} />
            </span>
          ))}
        </div>
      </Card>
    </div>
  );
}
