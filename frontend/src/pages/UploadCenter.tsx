import { Box, CheckCircle2, FileArchive, Globe2, LoaderCircle, ScanLine, TerminalSquare } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiErrorMessage, scansApi } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui";
import type { Criticality, Scan } from "../types/api";

type ScanKind = "repository" | "docker" | "tls";

function scanStage(scan: Scan): string {
  if (scan.status === "failed") return "Failed";
  if (scan.status === "completed") return "Completed";
  if (scan.progress < 30) return "Scanning";
  if (scan.progress < 65) return "Analyzing";
  if (scan.progress < 90) return "Generating CBOM";
  return "Finalizing";
}

export function UploadCenter() {
  const [projectName, setProjectName] = useState("SecureBank Enterprise");
  const [criticality, setCriticality] = useState<Criticality>("critical");
  const [file, setFile] = useState<File | null>(null);
  const [dockerImage, setDockerImage] = useState("nginx:1.27-alpine");
  const [tlsEndpoint, setTlsEndpoint] = useState("example.com:443");
  const [active, setActive] = useState<ScanKind | null>(null);
  const [scan, setScan] = useState<Scan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!scan || !["queued", "running"].includes(scan.status)) return;
    const timer = window.setInterval(async () => {
      try {
        setScan(await scansApi.get(scan.id));
      } catch (pollError) {
        setError(apiErrorMessage(pollError));
      }
    }, 1_300);
    return () => window.clearInterval(timer);
  }, [scan]);

  async function submit(kind: ScanKind, event: FormEvent) {
    event.preventDefault();
    setError(null);
    setActive(kind);
    try {
      const next =
        kind === "repository"
          ? file
            ? await scansApi.repository(file, projectName, criticality)
            : (() => { throw new Error("Choose a repository ZIP before starting the scan"); })()
          : kind === "docker"
            ? await scansApi.docker(dockerImage, projectName, criticality)
            : await scansApi.tls(tlsEndpoint, projectName, criticality);
      setScan(next);
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setActive(null);
    }
  }

  const scanCards = [
    {
      kind: "repository" as const,
      icon: FileArchive,
      title: "Repository archive",
      description: "Analyze Python, Java, JavaScript, and C/C++ source plus dependency manifests.",
      input: (
        <button type="button" onClick={() => inputRef.current?.click()} className="flex min-h-28 w-full flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-black/10 px-4 text-center transition hover:border-brand-300/30 hover:bg-brand-400/[0.03]">
          <FileArchive className="h-6 w-6 text-brand-300" />
          <span className="mt-2 text-sm font-medium text-slate-200">{file?.name ?? "Choose repository ZIP"}</span>
          <span className="mt-1 text-[11px] text-slate-600">Maximum 50 MiB</span>
          <input ref={inputRef} className="hidden" type="file" accept=".zip,application/zip" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </button>
      ),
    },
    {
      kind: "docker" as const,
      icon: Box,
      title: "Docker image",
      description: "Inspect packages, OpenSSL versions, cryptographic libraries, and configuration files.",
      input: <TextInput icon={<TerminalSquare className="h-4 w-4" />} value={dockerImage} onChange={setDockerImage} placeholder="registry/image:tag" />,
    },
    {
      kind: "tls" as const,
      icon: Globe2,
      title: "TLS endpoint",
      description: "Collect the negotiated protocol, cipher suite, certificate, and public key details.",
      input: <TextInput icon={<Globe2 className="h-4 w-4" />} value={tlsEndpoint} onChange={setTlsEndpoint} placeholder="example.com:443" />,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Discovery intake" title="Upload center" description="Start normalized discovery jobs from source repositories, container images, or live TLS endpoints." />

      <Card className="grid gap-4 p-5 md:grid-cols-[1fr_220px] md:p-6">
        <label className="block"><span className="mb-2 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Project name</span><input value={projectName} onChange={(event) => setProjectName(event.target.value)} className="field" /></label>
        <label className="block"><span className="mb-2 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Criticality</span><select value={criticality} onChange={(event) => setCriticality(event.target.value as Criticality)} className="field"><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
      </Card>

      <section className="grid gap-5 xl:grid-cols-3">
        {scanCards.map(({ kind, icon: Icon, title, description, input }) => (
          <form key={kind} onSubmit={(event) => void submit(kind, event)}>
            <Card className="flex h-full flex-col p-5 md:p-6">
              <span className="w-fit rounded-xl bg-brand-400/10 p-3 text-brand-300"><Icon className="h-5 w-5" /></span>
              <h2 className="mt-5 font-semibold text-white">{title}</h2>
              <p className="mt-2 min-h-12 text-xs leading-5 text-slate-500">{description}</p>
              <div className="mt-5">{input}</div>
              <button disabled={active !== null || !projectName.trim()} className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl border border-brand-300/20 bg-brand-400/10 px-4 py-2.5 text-sm font-bold text-brand-200 transition hover:bg-brand-400/15 disabled:cursor-not-allowed disabled:opacity-50">
                {active === kind ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />} Analyze {kind}
              </button>
            </Card>
          </form>
        ))}
      </section>

      {error && <div className="rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

      {scan && (
        <Card className="overflow-hidden">
          <div className="flex flex-col gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center md:justify-between md:px-6">
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-brand-400/10 p-2.5 text-brand-300">{scan.status === "completed" ? <CheckCircle2 className="h-5 w-5" /> : <ScanLine className="h-5 w-5" />}</span>
              <div><p className="font-medium text-white">{scan.target}</p><p className="mt-1 text-xs capitalize text-slate-500">{scan.source_type} scan · {scan.id.slice(0, 8)}</p></div>
            </div>
            <StatusBadge status={scan.status} />
          </div>
          <div className="p-5 md:p-6">
            <div className="mb-2 flex justify-between text-xs"><span className="text-slate-500">{scanStage(scan)}</span><span className="font-semibold text-slate-300">{scan.progress}%</span></div>
            <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-brand-300 transition-all duration-700" style={{ width: `${scan.progress}%` }} /></div>
            {scan.error_message && <p className="mt-4 text-sm text-rose-300">{scan.error_message}</p>}
            {scan.status === "completed" && (
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <p className="mr-auto text-sm text-slate-400"><span className="font-semibold text-white">{(scan.summary.assets_discovered as number | undefined) ?? 0}</span> assets normalized, scored, and mapped.</p>
                <a href={scansApi.cbomUrl(scan.id)} target="_blank" rel="noreferrer" className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-white/5">View CBOM JSON</a>
                <Link to="/assets" className="rounded-lg bg-brand-400 px-3 py-2 text-xs font-bold text-ink-950">Explore assets</Link>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

function TextInput({ icon, value, onChange, placeholder }: { icon: React.ReactNode; value: string; onChange: (value: string) => void; placeholder: string }) {
  return <div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600">{icon}</span><input required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="field pl-10" /></div>;
}
