import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Building2, Fingerprint, Radar, ShieldCheck, Sparkles, UserPlus } from "lucide-react";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [organizationName, setOrganizationName] = useState("");
  const [industry, setIndustry] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register({
        organization_name: organizationName,
        industry: industry.trim() ? industry.trim() : undefined,
        username,
        email,
        password,
      });
      navigate("/", { replace: true });
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen font-sans lg:grid-cols-2" style={{ background: "var(--bg-app)" }}>
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
            Onboard your organization
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/75">
            Creates a new, isolated tenant and your first administrator account in one step —
            no shared demo data, no manual setup.
          </p>
          <div className="mt-8 flex flex-col gap-3">
            {[
              { icon: Building2, text: "Dedicated, isolated organization tenant" },
              { icon: ShieldCheck, text: "First account gets full administrator access" },
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
            <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>Create your organization</h1>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              This creates a new tenant and signs you in as its first administrator.
            </p>
          </div>

          <form className="space-y-3.5" onSubmit={submit}>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Organization name
              </label>
              <input
                className="field font-medium"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                placeholder="e.g. Acme Bank"
                minLength={2}
                required
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Industry <span className="normal-case" style={{ color: "var(--text-muted)" }}>(optional)</span>
              </label>
              <input
                className="field font-medium"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Financial Services"
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Admin username
              </label>
              <input
                className="field font-medium"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                pattern="[A-Za-z0-9_.-]+"
                title="Letters, numbers, underscore, dot, and hyphen only"
                minLength={3}
                required
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Admin email
              </label>
              <input
                type="email"
                className="field font-medium"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                Password <span className="normal-case" style={{ color: "var(--text-muted)" }}>(min 12 characters)</span>
              </label>
              <input
                type="password"
                className="field"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={12}
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
              <UserPlus className="h-3.5 w-3.5" />
              <span>{loading ? "Creating organization..." : "Create organization"}</span>
            </button>
          </form>

          <p className="mt-6 text-center text-xs" style={{ color: "var(--text-muted)" }}>
            Already have an account?{" "}
            <Link to="/login" className="font-semibold" style={{ color: "var(--accent)" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
