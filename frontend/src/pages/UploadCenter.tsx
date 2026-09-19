import {
  Box,
  CheckCircle2,
  FileArchive,
  Globe2,
  Loader2,
  Play,
  TerminalSquare,
  UploadCloud,
  FileCode2,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiErrorMessage, scansApi } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui";
import type { Criticality, Scan } from "../types/api";

type ScanKind = "repository" | "docker" | "tls";

function scanStage(scan: Scan): string {
  if (scan.status === "failed") return "PIPELINE_FAILED";
  if (scan.status === "completed") return "CBOM_GENERATION_COMPLETE";
  if (scan.progress < 30) return "AST_STATIC_ANALYSIS";
  if (scan.progress < 65) return "CRYPTOGRAPHIC_NORM_IN_PROGRESS";
  if (scan.progress < 90) return "TOPOLOGY_GRAPH_PROJECTION";
  return "FINALIZING_INGESTION";
}

export function UploadCenter() {
  const [projectName, setProjectName] = useState("SecureBank Enterprise Core");
  const [criticality, setCriticality] = useState<Criticality>("critical");
  const [selectedKind, setSelectedKind] = useState<ScanKind>("repository");
  const [file, setFile] = useState<File | null>(null);
  const [dockerImage, setDockerImage] = useState("nginx:1.27-alpine");
  const [tlsEndpoint, setTlsEndpoint] = useState("api.securebank.internal:443");
  const [activeSubmitting, setActiveSubmitting] = useState<boolean>(false);
  const [scan, setScan] = useState<Scan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!scan || !["queued", "running"].includes(scan.status)) return;
    const timer = window.setInterval(async () => {
      try {
        setScan(await scansApi.get(scan.id));
      } catch (pollError) {
        setError(apiErrorMessage(pollError));
      }
    }, 1_200);
    return () => window.clearInterval(timer);
  }, [scan]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setActiveSubmitting(true);
    try {
      let next: Scan;
      if (selectedKind === "repository") {
        if (!file) {
          throw new Error("Target archive required. Select or drag a valid ZIP package.");
        }
        next = await scansApi.repository(file, projectName, criticality);
      } else if (selectedKind === "docker") {
        next = await scansApi.docker(dockerImage, projectName, criticality);
      } else {
        next = await scansApi.tls(tlsEndpoint, projectName, criticality);
      }
      setScan(next);
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setActiveSubmitting(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Discovery Intake Console"
        title="Upload Center"
        description="Ingest source code repositories, container images, or external TLS endpoints to extract CBOM artifacts and assess quantum cryptographic exposure."
      />

      {/* Unified Ingestion Control Panel */}
      <Card className="overflow-hidden border-zinc-300 shadow-subtle">
        {/* Scope Configuration Bar */}
        <div className="grid gap-3 border-b border-zinc-200 bg-zinc-50/70 p-4 md:grid-cols-[1fr_220px]">
          <div>
            <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1.5">
              Project Identifier
            </label>
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Core-Banking-Auth-Service"
              className="field font-medium text-zinc-950"
            />
          </div>
          <div>
            <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1.5">
              Business Criticality Tier
            </label>
            <select
              value={criticality}
              onChange={(e) => setCriticality(e.target.value as Criticality)}
              className="field font-mono text-xs text-zinc-950"
            >
              <option value="critical">Tier-1 Critical (Production Core)</option>
              <option value="high">Tier-2 High (Internal Services)</option>
              <option value="medium">Tier-3 Medium (Support Infrastructure)</option>
              <option value="low">Tier-4 Low (Ephemeral / Sandbox)</option>
            </select>
          </div>
        </div>

        {/* Ingestion Source Segmented Control */}
        <div className="flex border-b border-zinc-200 bg-zinc-100/50 p-1">
          <button
            type="button"
            onClick={() => setSelectedKind("repository")}
            className={`flex items-center gap-2 rounded px-3.5 py-2 font-mono text-xs font-semibold transition ${
              selectedKind === "repository"
                ? "bg-white text-zinc-950 shadow-xs border border-zinc-200/80"
                : "text-zinc-600 hover:text-zinc-950"
            }`}
          >
            <FileArchive className="h-3.5 w-3.5 text-zinc-700" strokeWidth={1.75} />
            Source Repository (.zip)
          </button>
          <button
            type="button"
            onClick={() => setSelectedKind("docker")}
            className={`flex items-center gap-2 rounded px-3.5 py-2 font-mono text-xs font-semibold transition ${
              selectedKind === "docker"
                ? "bg-white text-zinc-950 shadow-xs border border-zinc-200/80"
                : "text-zinc-600 hover:text-zinc-950"
            }`}
          >
            <Box className="h-3.5 w-3.5 text-zinc-700" strokeWidth={1.75} />
            Container Image (OCI / Docker)
          </button>
          <button
            type="button"
            onClick={() => setSelectedKind("tls")}
            className={`flex items-center gap-2 rounded px-3.5 py-2 font-mono text-xs font-semibold transition ${
              selectedKind === "tls"
                ? "bg-white text-zinc-950 shadow-xs border border-zinc-200/80"
                : "text-zinc-600 hover:text-zinc-950"
            }`}
          >
            <Globe2 className="h-3.5 w-3.5 text-zinc-700" strokeWidth={1.75} />
            Live TLS Endpoint
          </button>
        </div>

        {/* Interactive Ingestion Form */}
        <form onSubmit={handleSubmit} className="p-5">
          {selectedKind === "repository" && (
            <div className="space-y-4">
              {/* Drag & Drop Zone with high-contrast WCAG styling */}
              <div
                role="button"
                tabIndex={0}
                aria-label="Upload source code repository archive"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    inputRef.current?.click();
                  }
                }}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                  if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
                }}
                onClick={() => inputRef.current?.click()}
                className={`relative flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded border border-dashed transition p-6 text-center ${
                  dragActive
                    ? "border-indigo-600 bg-indigo-50/40"
                    : file
                      ? "border-emerald-600 bg-emerald-50/20"
                      : "border-zinc-300 bg-zinc-50/60 hover:border-zinc-500 hover:bg-zinc-100/40"
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".zip,application/zip"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="hidden"
                />

                <div className="flex h-9 w-9 items-center justify-center rounded border border-zinc-300 bg-white mb-2 shadow-xs text-zinc-800">
                  {file ? (
                    <FileCode2 className="h-5 w-5 text-emerald-700" strokeWidth={1.75} />
                  ) : (
                    <UploadCloud className="h-5 w-5 text-zinc-700" strokeWidth={1.75} />
                  )}
                </div>

                {file ? (
                  <div>
                    <p className="font-mono text-xs font-bold text-zinc-950">{file.name}</p>
                    <p className="font-mono text-[11px] text-zinc-600 mt-0.5">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB · Ready for AST parser ingestion
                    </p>
                    <span className="inline-block mt-2 font-mono text-[10px] text-indigo-700 underline font-medium">
                      Click to replace archive
                    </span>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-semibold text-zinc-900">
                      Drag and drop repository archive here, or <span className="text-indigo-600 underline">browse</span>
                    </p>
                    <p className="font-mono text-[11px] text-zinc-500 mt-1">
                      Target formats: .ZIP (Max 50MB) · Parses Python, Java, JS/TS, Go, C/C++ source & manifests
                    </p>
                  </div>
                )}
              </div>

              {/* Technical Parser Matrix Callout */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px] text-zinc-600">
                <div className="rounded border border-zinc-200 bg-zinc-50 px-2.5 py-1.5">
                  <span className="text-zinc-400 block text-[9px] uppercase">Engine</span>
                  <span className="font-semibold text-zinc-900">AST Static Probe</span>
                </div>
                <div className="rounded border border-zinc-200 bg-zinc-50 px-2.5 py-1.5">
                  <span className="text-zinc-400 block text-[9px] uppercase">Extraction</span>
                  <span className="font-semibold text-zinc-900">Sandboxed Unpack</span>
                </div>
                <div className="rounded border border-zinc-200 bg-zinc-50 px-2.5 py-1.5">
                  <span className="text-zinc-400 block text-[9px] uppercase">Artifact</span>
                  <span className="font-semibold text-zinc-900">CycloneDX CBOM</span>
                </div>
                <div className="rounded border border-zinc-200 bg-zinc-50 px-2.5 py-1.5">
                  <span className="text-zinc-400 block text-[9px] uppercase">Graph</span>
                  <span className="font-semibold text-zinc-900">Topology Projection</span>
                </div>
              </div>
            </div>
          )}

          {selectedKind === "docker" && (
            <div className="space-y-3">
              <div>
                <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1.5">
                  Container Image Reference (Registry / Repository:Tag)
                </label>
                <div className="relative">
                  <TerminalSquare className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
                  <input
                    required
                    value={dockerImage}
                    onChange={(e) => setDockerImage(e.target.value)}
                    placeholder="e.g. docker.io/library/nginx:1.27-alpine"
                    className="field font-mono text-xs pl-8 text-zinc-950"
                  />
                </div>
              </div>
              <p className="font-mono text-[11px] text-zinc-500">
                Deconstructs image layers to inspect installed OpenSSL/BoringSSL packages, cryptographic shared objects (.so/.dylib), and runtime TLS configuration profiles.
              </p>
            </div>
          )}

          {selectedKind === "tls" && (
            <div className="space-y-3">
              <div>
                <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1.5">
                  Target Hostname & Port
                </label>
                <div className="relative">
                  <Globe2 className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
                  <input
                    required
                    value={tlsEndpoint}
                    onChange={(e) => setTlsEndpoint(e.target.value)}
                    placeholder="e.g. secure.bank.corp:443"
                    className="field font-mono text-xs pl-8 text-zinc-950"
                  />
                </div>
              </div>
              <p className="font-mono text-[11px] text-zinc-500">
                Performs an active SSL/TLS handshake probe collecting supported protocol versions, negotiated cipher suites, root trust anchors, certificate validity, and public key bit-lengths.
              </p>
            </div>
          )}

          {/* Action Row */}
          <div className="mt-5 flex items-center justify-between border-t border-zinc-200 pt-4">
            <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-500">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Deterministic Rule-Engine & Evidence Correlator Enabled</span>
            </div>

            <button
              type="submit"
              disabled={activeSubmitting || !projectName.trim()}
              className="btn-primary"
            >
              {activeSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Dispatching Scan Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Execute {selectedKind.toUpperCase()} Intake</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Card>

      {/* Error alert */}
      {error && (
        <div className="flex items-start gap-2.5 rounded border border-red-300 bg-red-50/90 p-3 text-xs text-red-900 font-mono">
          <AlertTriangle className="h-4 w-4 text-red-700 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Execution Error</p>
            <p className="mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Active Pipeline Telemetry Console */}
      {scan && (
        <Card className="overflow-hidden border-zinc-300 shadow-subtle">
          <div className="flex flex-col gap-2 border-b border-zinc-200 bg-zinc-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded border border-zinc-300 bg-white">
                {scan.status === "completed" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                )}
              </div>
              <div>
                <p className="font-mono text-xs font-bold text-zinc-950">{scan.target}</p>
                <p className="font-mono text-[10px] text-zinc-500 uppercase">
                  {scan.source_type} Discovery · Scan ID: {scan.id.slice(0, 8)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={scan.status} />
            </div>
          </div>

          <div className="p-4 space-y-3">
            {/* Stage & Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between font-mono text-[11px]">
                <span className="text-zinc-600 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                  Stage: <strong className="text-zinc-900">{scanStage(scan)}</strong>
                </span>
                <span className="font-bold text-zinc-950">{scan.progress}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 border border-zinc-200">
                <div
                  className="h-full bg-indigo-600 transition-all duration-500"
                  style={{ width: `${scan.progress}%` }}
                />
              </div>
            </div>

            {scan.error_message && (
              <p className="font-mono text-xs text-red-700 bg-red-50 p-2 rounded border border-red-200">
                {scan.error_message}
              </p>
            )}

            {/* Completed Artifact & Navigation Bar */}
            {scan.status === "completed" && (
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-zinc-100">
                <p className="font-mono text-xs text-zinc-700">
                  <span className="font-bold text-zinc-950 text-sm">
                    {(scan.summary.assets_discovered as number | undefined) ?? 0}
                  </span>{" "}
                  cryptographic assets normalized & mapped to dependency graph.
                </p>
                <div className="flex items-center gap-2">
                  <a
                    href={scansApi.cbomUrl(scan.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                  >
                    <ExternalLink className="h-3 w-3 text-zinc-500" />
                    <span>View CBOM JSON</span>
                  </a>
                  <Link to="/assets" className="btn-primary">
                    <span>Inspect Inventory</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
