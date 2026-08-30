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
    <main className="grid min-h-screen place-items-center bg-ink-950 px-5 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-white/[0.08] bg-ink-900/90 p-8 shadow-2xl">
        <div className="mb-8 flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl border border-brand-300/30 bg-brand-400/10"><Radar className="h-5 w-5 text-brand-300" /></div><div><p className="font-extrabold tracking-[0.16em] text-white">ECDAT-X</p><p className="text-xs text-slate-500">Enterprise access</p></div></div>
        <h1 className="text-2xl font-bold text-white">Sign in to your organization</h1>
        <p className="mt-2 text-sm text-slate-500">Use your assigned administrator, analyst, auditor, or viewer account.</p>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <label className="block text-xs font-medium text-slate-400">Organization<input className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none focus:border-brand-300/50" value={organization} onChange={(e) => setOrganization(e.target.value)} required /></label>
          <label className="block text-xs font-medium text-slate-400">Username<input className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none focus:border-brand-300/50" value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
          <label className="block text-xs font-medium text-slate-400">Password<input type="password" className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none focus:border-brand-300/50" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          {error && <p className="rounded-lg border border-red-400/20 bg-red-400/10 px-3 py-2 text-xs text-red-300">{error}</p>}
          <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-300 px-4 py-3 text-sm font-bold text-ink-950 transition hover:bg-brand-200 disabled:opacity-60"><LockKeyhole className="h-4 w-4" />{loading ? "Signing in…" : "Sign in securely"}</button>
        </form>
      </div>
    </main>
  );
}
