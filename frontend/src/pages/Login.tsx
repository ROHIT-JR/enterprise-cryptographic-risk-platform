import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { LockKeyhole, Radar } from "lucide-react";
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
    <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl border border-blue-200 bg-blue-50">
            <Radar className="h-4.5 w-4.5 text-blue-600" />
          </div>
          <div>
            <p className="text-[14px] font-extrabold tracking-[0.14em] text-slate-900">ECDAT-X</p>
            <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-400">Enterprise access</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-panel">
          <h1 className="text-2xl font-semibold text-slate-900">Sign in to your organization</h1>
          <p className="mt-2 text-sm text-slate-400">Use your administrator, analyst, auditor, or viewer account.</p>

          <form className="mt-7 space-y-4" onSubmit={submit}>
            <label className="block text-xs font-medium text-slate-600">
              Organization
              <input
                className="field mt-2"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                required
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              Username
              <input
                className="field mt-2"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              Password
              <input
                type="password"
                className="field mt-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
                {error}
              </p>
            )}

            <button
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
            >
              <LockKeyhole className="h-4 w-4" />
              {loading ? "Signing in…" : "Sign in securely"}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
