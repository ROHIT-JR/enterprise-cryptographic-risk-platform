import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Fingerprint, LockKeyhole, Radar, ShieldCheck, Sparkles } from "lucide-react";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [organization, setOrganization] = useState("SecureBank");
  const [username, setUsername] = useState("security-analyst");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(organization, username, password);
      const destination = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(destination, { replace: true });
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen font-sans lg:grid-cols-2" style={{ background: "var(--bg-app)" }}>
      {/* Left: branded panel — first screen judges see */}
      <div
        className="relative hidden flex-col justify-between overflow-hidden p-10 lg:flex"
        style={{ background: "linear-gradient(155deg, var(--accent) 0%, var(--accent-hover) 55%, #1e1b4b 100%)" }}
      >
        <div className="pointer-events-none absolute inset-0 opacity-20" style={{
          backgroundImage: "radial-gradient(circle at 20% 20%, white 0, transparent 35%), radial-gradient(circle at 80% 70%, white 0, transparent 40%)",
        }} />
        <div className="relative flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 backdrop-blur-sm">
            <Radar className="h-5 w-5 text-white" strokeWidth={1.75} />
          </div>
          <div>
            <p className="font-mono text-sm font-bold tracking-widest text-white">ECDAT-X</p>
            <p className="font-mono text-[9px] uppercase tracking-wider text-white/70">Crypto Intel Engine</p>
          </div>
        </div>

        <div className="relative">
          <h1 className="max-w-md text-3xl font-bold leading-tight tracking-tight text-white">
            Enterprise Cryptographic Discovery &amp; Analysis Tool
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/75">
            Inventory every cryptographic asset, quantify quantum risk, and generate a defensible PQC migration plan — across source code, containers, and live TLS endpoints.
          </p>
          <div className="mt-8 flex flex-col gap-3">
            {[
              { icon: ShieldCheck, text: "Explainable, six-factor risk scoring" },
              { icon: Sparkles, text: "TOPSIS-ranked PQC migration recommendations" },
              { icon: Fingerprint, text: "Zero-trust, tenant-isolated access control" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-2.5 text-sm text-white/90">
                <Icon className="h-4 w-4 shrink-0 text-white/80" strokeWidth={1.75} />
                {text}
              </div>
            ))}
          </div>
        </div>

        <p className="relative font-mono text-[10px] uppercase tracking-widest text-white/50">
          Enterprise Scrypt Hash · Zero-Trust RBAC
        </p>
      </div>

      {/* Right: auth form */}
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg" style={{ background: "var(--accent)" }}>
              <Radar className="h-4 w-4 text-white" strokeWidth={1.75} />
            </div>
            <div>
              <p className="font-mono text-xs font-bold tracking-widest" style={{ color: "var(--text-primary)" }}>ECDAT-X</p>
              <p className="font-mono text-[9px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Cryptographic Operations Gateway</p>
            </div>
          </div>

          <div className="mb-6">
            <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>Welcome back</h1>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Authenticate using organization credentials for isolated cryptographic tenant access.
            </p>
          </div>

          <form className="space-y-3.5" onSubmit={submit}>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Organization Tenant
              </label>
              <input
                className="field font-medium"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Username Identifier
              </label>
              <input
                className="field font-medium"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Secret Access Token / Password
              </label>
              <input
                type="password"
                className="field"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <p
                className="rounded-lg border p-2.5 font-mono text-[11px]"
                style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 8%, transparent)", color: "var(--risk-critical)" }}
              >
                {error}
              </p>
            )}

            <button disabled={loading} className="btn-primary mt-2 w-full py-2.5">
              <LockKeyhole className="h-3.5 w-3.5" />
              <span>{loading ? "Authenticating Token..." : "Authenticate Session"}</span>
            </button>
          </form>

          <div className="mt-6 flex items-center justify-between px-1 font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
            <span>Enterprise Scrypt Hash</span>
            <span>Zero-Trust RBAC</span>
          </div>
        </div>
      </div>
    </main>
  );
}
