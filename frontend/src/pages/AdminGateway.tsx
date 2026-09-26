import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { KeyRound, ShieldAlert } from "lucide-react";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

// Fixed organization tenant for the platform administrator account created
// by the backend bootstrap (ECDAT_ADMIN_USERNAME/ECDAT_ADMIN_PASSWORD) —
// see backend/app/services/admin_bootstrap.py. Not user-editable: this page
// exists only to authenticate that one predefined account.
const PLATFORM_ORGANIZATION = "Platform";

export function AdminGateway() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to="/admin" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(PLATFORM_ORGANIZATION, username, password);
      navigate("/admin", { replace: true });
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="flex min-h-screen items-center justify-center px-4 font-sans"
      style={{ background: "var(--bg-app)" }}
    >
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div
            className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: "var(--risk-critical)" }}
          >
            <ShieldAlert className="h-5 w-5 text-white" strokeWidth={1.75} />
          </div>
          <h1 className="text-lg font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            Platform administrator access
          </h1>
          <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Restricted entry point. Credentials are provisioned out of band.
          </p>
        </div>

        <form
          className="space-y-3.5 rounded-xl border p-5"
          style={{ borderColor: "var(--border-strong)", background: "var(--bg-card)" }}
          onSubmit={submit}
        >
          <div>
            <label
              className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-secondary)" }}
            >
              Admin username
            </label>
            <input
              className="field font-medium"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label
              className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-secondary)" }}
            >
              Admin password
            </label>
            <input
              type="password"
              className="field"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p
              className="rounded-lg border p-2.5 font-mono text-[11px]"
              style={{
                borderColor: "var(--risk-critical)",
                background: "color-mix(in srgb, var(--risk-critical) 8%, transparent)",
                color: "var(--risk-critical)",
              }}
            >
              {error}
            </p>
          )}

          <button disabled={loading} className="btn-primary mt-1 w-full py-2.5">
            <KeyRound className="h-3.5 w-3.5" />
            <span>{loading ? "Authenticating..." : "Authenticate"}</span>
          </button>
        </form>
      </div>
    </main>
  );
}
