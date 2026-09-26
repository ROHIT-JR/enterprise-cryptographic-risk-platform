import { useState, type FormEvent } from "react";
import {
  Activity,
  AlertTriangle,
  Building2,
  Crown,
  Database,
  Eye,
  History,
  Network,
  PlusCircle,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { enterpriseApi, organizationsApi, usersApi, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Card, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { relativeTime } from "../utils/format";
import type { UserRole } from "../types/api";

const ROLES: { value: UserRole; label: string }[] = [
  { value: "administrator", label: "Administrator" },
  { value: "security_analyst", label: "Security analyst" },
  { value: "auditor", label: "Auditor" },
  { value: "viewer", label: "Viewer" },
];

export function AdminDashboard() {
  const { user } = useAuth();
  const isPlatformAdmin = user?.is_platform_admin ?? false;

  // "View as org" — a read-only override, only ever honored server-side for
  // the platform admin (see backend/app/auth/dependencies.py:resolve_org_id).
  // null means "my own organization". Every cross-org fetch below is
  // recorded in that organization's own audit trail by the backend.
  const [viewOrgId, setViewOrgId] = useState<string | null>(null);

  const { data: organizations, reload: reloadOrganizations } = useAsync(
    async () => (isPlatformAdmin ? organizationsApi.list() : []),
    [isPlatformAdmin],
  );

  const { data, error, loading, reload } = useAsync(
    async () => {
      const [overview, users, health, audit] = await Promise.all([
        enterpriseApi.overview(viewOrgId ?? undefined),
        usersApi.list(viewOrgId ?? undefined),
        enterpriseApi.health(),
        enterpriseApi.audit(viewOrgId ?? undefined),
      ]);
      return { overview, users, health, audit };
    },
    [viewOrgId],
  );

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("security_analyst");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [orgName, setOrgName] = useState("");
  const [orgIndustry, setOrgIndustry] = useState("");
  const [creatingOrg, setCreatingOrg] = useState(false);
  const [orgCreateError, setOrgCreateError] = useState<string | null>(null);

  const [deleteConfirmName, setDeleteConfirmName] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;

  const viewedOrg = organizations?.find((org) => org.id === viewOrgId) ?? null;
  const isCrossOrgView = viewOrgId != null;
  const highestPrivilegedUser =
    data.users.find((u) => u.role === "administrator") ?? data.users[0] ?? null;

  const metrics = [
    ["Organizations", data.overview.organizations, Building2], ["Users", data.overview.users, Users],
    ["Scans", data.overview.scans, Activity], ["Assets", data.overview.assets, Database],
  ] as const;

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      await usersApi.create({ username, email, password, role, organization_id: viewOrgId ?? undefined });
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

  async function createOrganization(event: FormEvent) {
    event.preventDefault();
    setCreatingOrg(true);
    setOrgCreateError(null);
    try {
      const created = await organizationsApi.create({
        name: orgName,
        industry: orgIndustry || undefined,
      });
      setOrgName("");
      setOrgIndustry("");
      await reloadOrganizations();
      setViewOrgId(created.id);
    } catch (reason) {
      setOrgCreateError(apiErrorMessage(reason));
    } finally {
      setCreatingOrg(false);
    }
  }

  async function deleteViewedOrganization() {
    if (!viewOrgId || !viewedOrg) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await organizationsApi.remove(viewOrgId, deleteConfirmName);
      setDeleteConfirmName("");
      setViewOrgId(null);
      await reloadOrganizations();
    } catch (reason) {
      setDeleteError(apiErrorMessage(reason));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Enterprise administration"
        title="Admin dashboard"
        description={
          isCrossOrgView
            ? `Viewing ${viewedOrg?.name ?? "another organization"} as the platform admin — read-only, audit-logged.`
            : "Your organization's identity, platform health, and tenant activity."
        }
      />

      {isPlatformAdmin && (
        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <Eye className="h-4 w-4" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
            <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              View as organization
            </p>
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Pick any organization to see exactly what its own administrator sees. This is read-only —
            every switch is recorded in that organization's audit trail.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <select
              className="field font-medium sm:w-72"
              value={viewOrgId ?? ""}
              onChange={(e) => setViewOrgId(e.target.value || null)}
            >
              <option value="">My organization</option>
              {organizations?.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
            {isCrossOrgView && (
              <button type="button" className="btn-secondary" onClick={() => setViewOrgId(null)}>
                Return to my organization
              </button>
            )}
          </div>

          <form onSubmit={createOrganization} className="mt-5 space-y-3 border-t pt-5" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2">
              <PlusCircle className="h-4 w-4" style={{ color: "var(--accent)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Create organization</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="field font-medium"
                placeholder="Organization name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                minLength={2}
                required
              />
              <input
                className="field font-medium"
                placeholder="Industry (optional)"
                value={orgIndustry}
                onChange={(e) => setOrgIndustry(e.target.value)}
              />
            </div>
            {orgCreateError && (
              <p
                className="rounded-lg border p-2.5 font-mono text-[11px]"
                style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 8%, transparent)", color: "var(--risk-critical)" }}
              >
                {orgCreateError}
              </p>
            )}
            <button disabled={creatingOrg} className="btn-primary">
              <PlusCircle className="h-3.5 w-3.5" />
              <span>{creatingOrg ? "Creating..." : "Create organization"}</span>
            </button>
          </form>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, Icon]) => (
          <Card key={label} className="card-hover p-5">
            <Icon className="h-5 w-5" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
            <p className="mt-4 font-mono text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>{value}</p>
          </Card>
        ))}
      </div>

      {isCrossOrgView && highestPrivilegedUser && (
        <Card className="p-5">
          <div className="flex items-center gap-2.5">
            <Crown className="h-4 w-4" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
            <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              Highest-privileged person in {viewedOrg?.name ?? "this organization"}
            </p>
          </div>
          <div className="mt-3 flex items-center justify-between rounded border px-4 py-3 text-sm" style={{ borderColor: "var(--border)" }}>
            <div>
              <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{highestPrivilegedUser.username}</p>
              <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{highestPrivilegedUser.email}</p>
            </div>
            <span
              className="rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold capitalize"
              style={{ borderColor: "var(--accent)", background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              {highestPrivilegedUser.role.replace("_", " ")}
            </span>
          </div>
        </Card>
      )}

      {isCrossOrgView && (
        <Card className="p-5" style={{ borderColor: "var(--risk-critical)" }}>
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4 w-4" style={{ color: "var(--risk-critical)" }} strokeWidth={1.75} />
            <p className="text-sm font-bold" style={{ color: "var(--risk-critical)" }}>
              Danger zone — delete {viewedOrg?.name ?? "this organization"}
            </p>
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            This permanently deletes the organization and everything it owns — every user, project,
            scan, asset, finding, and audit entry. This cannot be undone. Type the organization's
            exact name to confirm.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <input
              className="field font-medium sm:w-72"
              placeholder={viewedOrg?.name ?? "Organization name"}
              value={deleteConfirmName}
              onChange={(e) => setDeleteConfirmName(e.target.value)}
            />
            <button
              type="button"
              className="btn-primary"
              style={{ background: "var(--risk-critical)" }}
              disabled={deleting || deleteConfirmName !== viewedOrg?.name}
              onClick={() => void deleteViewedOrganization()}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{deleting ? "Deleting..." : "Delete organization"}</span>
            </button>
          </div>
          {deleteError && (
            <p
              className="mt-3 rounded-lg border p-2.5 font-mono text-[11px]"
              style={{ borderColor: "var(--risk-critical)", background: "color-mix(in srgb, var(--risk-critical) 8%, transparent)", color: "var(--risk-critical)" }}
            >
              {deleteError}
            </p>
          )}
        </Card>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
            {isCrossOrgView ? `${viewedOrg?.name ?? "Organization"} users` : "Organization users"}
          </p>
          <div className="mt-4 divide-y" style={{ borderColor: "var(--border)" }}>
            {data.users.map((u) => (
              <div key={u.id} className="flex items-center justify-between py-3 text-sm" style={{ borderColor: "var(--border)" }}>
                <div>
                  <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{u.username}</p>
                  <p className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{u.email}</p>
                </div>
                <span
                  className="rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold capitalize"
                  style={{ borderColor: "var(--accent)", background: "var(--accent-soft)", color: "var(--accent)" }}
                >
                  {u.role.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>

          <form onSubmit={createUser} className="mt-5 space-y-3 border-t pt-5" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2">
              <UserPlus className="h-4 w-4" style={{ color: "var(--accent)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                {isCrossOrgView ? `Add user to ${viewedOrg?.name ?? "organization"}` : "Add user"}
              </p>
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

      <Card className="p-5">
        <div className="flex items-center gap-2.5">
          <History className="h-4 w-4" style={{ color: "var(--accent)" }} strokeWidth={1.75} />
          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
            {isCrossOrgView ? `${viewedOrg?.name ?? "Organization"} audit trail` : "Audit trail"}
          </p>
        </div>
        <div className="mt-3 divide-y" style={{ borderColor: "var(--border)" }}>
          {data.audit.map((entry) => (
            <div key={entry.id} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div>
                <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{entry.action.replaceAll(".", " ")}</p>
                <p className="mt-0.5 font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>{entry.user_id ?? "system"}</p>
              </div>
              <span className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{relativeTime(entry.timestamp)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
