import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { LockKeyhole, Radar, Shield } from "lucide-react";
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
    <main className="grid min-h-screen place-items-center bg-[#fafafa] px-4 font-sans">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-700 bg-zinc-950 text-white">
            <Radar className="h-4 w-4 text-indigo-400" strokeWidth={1.75} />
          </div>
          <div>
            <p className="font-mono text-xs font-bold tracking-widest text-zinc-950">ECDAT-X</p>
            <p className="font-mono text-[9px] uppercase tracking-wider text-zinc-500">Cryptographic Operations Gateway</p>
          </div>
        </div>

        <div className="rounded-md border border-zinc-200 bg-white p-6 shadow-subtle">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3 mb-4">
            <h1 className="text-sm font-bold tracking-tight text-zinc-950">Organization Authentication</h1>
            <Shield className="h-4 w-4 text-zinc-400" />
          </div>
          <p className="font-mono text-[11px] text-zinc-500 mb-4 leading-normal">
            Authenticate using organization credentials for isolated cryptographic tenant access.
          </p>

          <form className="space-y-3" onSubmit={submit}>
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1">
                Organization Tenant
              </label>
              <input
                className="field font-medium text-zinc-950"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1">
                Username Identifier
              </label>
              <input
                className="field font-medium text-zinc-950"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-1">
                Secret Access Token / Password
              </label>
              <input
                type="password"
                className="field text-zinc-950"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <p className="rounded border border-red-300 bg-red-50 p-2 font-mono text-[11px] text-red-900">
                {error}
              </p>
            )}

            <button
              disabled={loading}
              className="btn-primary w-full mt-2 py-2"
            >
              <LockKeyhole className="h-3.5 w-3.5" />
              <span>{loading ? "Authenticating Token..." : "Authenticate Session"}</span>
            </button>
          </form>
        </div>

        <div className="mt-4 flex items-center justify-between font-mono text-[10px] text-zinc-400 px-1">
          <span>Enterprise Scrypt Hash</span>
          <span>Zero-Trust RBAC</span>
        </div>
      </div>
    </main>
  );
}
