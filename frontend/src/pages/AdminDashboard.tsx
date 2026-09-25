import { useState, type FormEvent } from "react";
import { Activity, Building2, Database, Network, UserPlus, Users } from "lucide-react";
import { enterpriseApi, usersApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import type { UserRole } from "../types/api";

const ROLES: { value: UserRole; label: string }[] = [
  { value: "administrator", label: "Administrator" },
  { value: "security_analyst", label: "Security analyst" },
  { value: "auditor", label: "Auditor" },
  { value: "viewer", label: "Viewer" },
];

export function AdminDashboard() {
  const { data, error, loading, reload } = useAsync(
    async () => {
      const [overview, organization, users, health] = await Promise.all([
        enterpriseApi.overview(), enterpriseApi.organization(), enterpriseApi.users(), enterpriseApi.health(),
      ]);
      return { overview, organization, users, health };
    },
    [],
  );
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("security_analyst");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [
    ["Organizations", data.overview.organizations, Building2], ["Users", data.overview.users, Users],
    ["Scans", data.overview.scans, Activity], ["Assets", data.overview.assets, Database],
  ] as const;

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await usersApi.create({ username, email, password, role });
      setUsername("");
      setEmail("");
      setPassword("");
      setRole("security_analyst");
      await reload();
    } catch (reason) {
      setCreateError(apiErrorMessage(reason));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Enterprise administration"
        title="Admin dashboard"
        description={`${data.organization.name} identity, platform health, and tenant activity.`}
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, Icon]) => (
          <Card key={label} className="card-hover p-5">
            <Icon className="h-5 w-5" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
            <p className="mt-4 font-mono text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>{value}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Organization users</p>
          <div className="mt-4 divide-y" style={{ borderColor: "var(--border)" }}>
            {data.users.map((user) => (
              <div key={user.id} className="flex items-center justify-between py-3 text-sm" style={{ borderColor: "var(--border)" }}>
                <div>
                  <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{user.username}</p>
                  <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{user.email}</p>
                </div>
                <span
                  className="rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold capitalize"
                  style={{ borderColor: "var(--accent)", background: "var(--accent-soft)", color: "var(--accent)" }}
                >
                  {user.role.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>

          <form onSubmit={createUser} className="mt-5 space-y-3 border-t pt-5" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2">
              <UserPlus className="h-4 w-4" style={{ color: "var(--accent)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Add user</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="field font-medium"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                pattern="[A-Za-z0-9_.-]+"
                minLength={3}
                required
              />
              <input
                type="email"
                className="field font-medium"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <input
                type="password"
                className="field"
                placeholder="Password (min 12 characters)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={12}
                required
              />
              <select
                className="field font-medium"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            {createError && (
              <p
                className="rounded-lg border p-2.5 font-mono text-[11px]"
                style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 8%, transparent)", color: "var(--risk-critical)" }}
              >
                {createError}
              </p>
            )}
            <button disabled={creating} className="btn-primary">
              <UserPlus className="h-3.5 w-3.5" />
              <span>{creating ? "Adding..." : "Add user"}</span>
            </button>
          </form>
        </Card>
        <Card className="p-5">
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>System health</p>
          <div className="mt-4 space-y-2.5">
            {Object.entries(data.health)
              .filter(([key]) => key !== "scanners")
              .map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded border px-4 py-3 text-sm"
                  style={{ borderColor: "var(--border)", background: "var(--bg-hover)" }}
                >
                  <span className="flex items-center gap-2 font-medium capitalize" style={{ color: "var(--text-secondary)" }}>
                    <Network className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
                    {key.replace("_", " ")}
                  </span>
                  <span className="font-mono text-xs font-bold" style={{ color: "var(--risk-low)" }}>{String(value)}</span>
                </div>
              ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
